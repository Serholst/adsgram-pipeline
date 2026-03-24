"""Apollo.io API client with rate limiting, retries, and credit tracking."""

from __future__ import annotations

import json
import logging
import time
from datetime import date
from pathlib import Path
from typing import Any

import requests
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from config import (
    API_BASE_URL,
    APOLLO_API_KEY,
    CREDIT_TRACKER_FILE,
    DAILY_CREDIT_LIMIT,
    RATE_LIMIT_RPM,
    REQUEST_TIMEOUT,
)

log = logging.getLogger(__name__)


class ApolloAPIError(Exception):
    """Non-retryable API error."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ApolloAuthError(ApolloAPIError):
    """401/403 — invalid or expired API key."""
    pass


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, ApolloAPIError):
        return exc.status_code in (429, 500, 502, 503, 504)
    if isinstance(exc, requests.exceptions.ConnectionError):
        return True
    if isinstance(exc, requests.exceptions.Timeout):
        return True
    return False


class ApolloClient:
    def __init__(self, api_key: str = APOLLO_API_KEY) -> None:
        self.session = requests.Session()
        self.session.headers.update({
            "X-Api-Key": api_key,
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "Accept": "application/json",
        })
        self._min_interval = 60.0 / RATE_LIMIT_RPM  # ~1.2s for 50 rpm
        self._last_request_time = 0.0
        self._credit_file = CREDIT_TRACKER_FILE

    # --- Public API ---

    def enrich_organization(self, domain: str) -> dict[str, Any] | None:
        """Enrich an organization via /organizations/enrich. Returns org dict or None.

        Returns industry, keywords, company info. Costs 1 credit.
        """
        self._increment_credits()
        resp = self._request("GET", f"/organizations/enrich?domain={domain}")
        org = resp.get("organization")
        if not org:
            log.info("No org match for domain %s", domain)
            return None
        return org

    def enrich_person(
        self,
        first_name: str,
        last_name: str,
        domain: str | None = None,
        organization_name: str | None = None,
        linkedin_url: str | None = None,
    ) -> dict[str, Any] | None:
        """Enrich a person via /people/match. Returns parsed person dict or None.

        Only returns data if email_status is verified. Costs 1 credit.
        """
        payload: dict[str, Any] = {
            "first_name": first_name,
            "last_name": last_name,
        }
        if domain:
            payload["domain"] = domain
        if organization_name:
            payload["organization_name"] = organization_name
        if linkedin_url:
            payload["linkedin_url"] = linkedin_url

        # Increment credit BEFORE call (safe on crash — slightly overcount rather than undercount)
        self._increment_credits()

        resp = self._request("POST", "/people/match", payload)
        person = resp.get("person")
        if not person:
            log.info("No match for %s %s", first_name, last_name)
            return None

        email = person.get("email")
        email_status = person.get("email_status")
        if not email or email_status != "verified":
            log.info(
                "Match found for %s %s but email not verified (status=%s)",
                first_name, last_name, email_status,
            )
            # Still return person data (title, linkedin, etc.) but without email
            person["email"] = None

        return person

    def search_people(
        self,
        organization_domains: list[str],
        person_titles: list[str],
        per_page: int = 100,
        max_pages: int = 1,
    ) -> list[dict[str, Any]]:
        """Search people via /mixed_people/api_search. FREE — no credits consumed.

        Returns list of person dicts. Does NOT include email addresses.
        """
        all_people: list[dict[str, Any]] = []

        for page in range(1, max_pages + 1):
            payload = {
                "person_titles": person_titles,
                "q_organization_domains": "\n".join(organization_domains),
                "page": page,
                "per_page": per_page,
            }
            resp = self._request("POST", "/mixed_people/search", payload)
            people = resp.get("people", [])
            if not people:
                break
            all_people.extend(people)
            log.info("Search page %d: got %d results", page, len(people))

            total = resp.get("pagination", {}).get("total_entries", 0)
            if len(all_people) >= total:
                break

        return all_people

    def create_contact(self, contact_data: dict[str, Any], dedupe: bool = True) -> str:
        """Create a contact in Apollo CRM. Returns apollo_id."""
        payload = {**contact_data}
        if dedupe:
            payload["run_dedupe"] = True

        resp = self._request("POST", "/contacts", payload)
        contact = resp.get("contact", {})
        apollo_id = contact.get("id", "")
        if apollo_id:
            log.info("Created/found contact in Apollo: %s", apollo_id)
        return apollo_id

    def update_contact(self, apollo_id: str, contact_data: dict[str, Any]) -> bool:
        """Update an existing contact in Apollo CRM."""
        self._request("PATCH", f"/contacts/{apollo_id}", contact_data)
        log.info("Updated contact %s in Apollo", apollo_id)
        return True

    # --- Credit tracking ---

    def credits_used_today(self) -> int:
        data = self._load_credits()
        if data.get("date") != str(date.today()):
            return 0
        return data.get("used", 0)

    def credits_remaining_today(self) -> int:
        return max(0, DAILY_CREDIT_LIMIT - self.credits_used_today())

    def check_credit_budget(self, needed: int) -> None:
        """Warn or abort if insufficient credits."""
        remaining = self.credits_remaining_today()
        if needed > remaining:
            raise ApolloAPIError(
                f"Insufficient credits: need {needed}, only {remaining} remaining today "
                f"(limit: {DAILY_CREDIT_LIMIT}). Adjust --limit or try again tomorrow."
            )
        used = self.credits_used_today()
        warn_threshold = int(DAILY_CREDIT_LIMIT * 0.8)
        if used >= warn_threshold:
            log.warning(
                "Credit usage at %d/%d (%.0f%%). Approaching daily limit.",
                used, DAILY_CREDIT_LIMIT, used / DAILY_CREDIT_LIMIT * 100,
            )

    # --- Internal ---

    @retry(
        retry=retry_if_exception(_is_retryable),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def _request(self, method: str, endpoint: str, payload: dict | None = None) -> dict:
        """Make rate-limited, retryable API request."""
        # Rate limiting
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.monotonic()

        url = f"{API_BASE_URL}{endpoint}"
        log.debug("API %s %s", method, url)

        try:
            resp = self.session.request(
                method=method,
                url=url,
                json=payload,
                timeout=REQUEST_TIMEOUT,
            )
        except requests.exceptions.Timeout:
            log.warning("Request timeout: %s %s", method, endpoint)
            raise ApolloAPIError(f"Request timed out: {endpoint}", status_code=None)
        except requests.exceptions.ConnectionError as e:
            log.warning("Connection error: %s", e)
            raise

        # Handle errors
        if resp.status_code in (401, 403):
            raise ApolloAuthError(
                "Invalid or expired API key. Check APOLLO_API_KEY in your .env file.",
                status_code=resp.status_code,
            )
        if resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After", "60")
            log.warning("Rate limited (429). Retry-After: %s", retry_after)
            raise ApolloAPIError(f"Rate limited. Retry after {retry_after}s", status_code=429)
        if resp.status_code >= 500:
            raise ApolloAPIError(
                f"Server error {resp.status_code}: {resp.text[:200]}",
                status_code=resp.status_code,
            )
        if resp.status_code == 422:
            raise ApolloAPIError(
                f"Bad request (422): {resp.text[:300]}",
                status_code=422,
            )
        if not resp.ok:
            raise ApolloAPIError(
                f"API error {resp.status_code}: {resp.text[:300]}",
                status_code=resp.status_code,
            )

        return resp.json()

    def _increment_credits(self) -> None:
        data = self._load_credits()
        today = str(date.today())
        if data.get("date") != today:
            data = {"date": today, "used": 0}
        data["used"] = data.get("used", 0) + 1
        self._save_credits(data)

    def _load_credits(self) -> dict:
        if not self._credit_file.exists():
            return {"date": str(date.today()), "used": 0}
        try:
            return json.loads(self._credit_file.read_text())
        except (json.JSONDecodeError, OSError):
            return {"date": str(date.today()), "used": 0}

    def _save_credits(self, data: dict) -> None:
        try:
            self._credit_file.write_text(json.dumps(data, indent=2))
        except OSError as e:
            log.warning("Could not save credit tracker: %s", e)
