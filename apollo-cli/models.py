"""Data models for Apollo Outreach CLI tool.

Two-sheet Excel:
  Sheet "Companies": #, Country, Company, Company Domain, Business Domain, Apollo ID
  Sheet "Employees": Company, Contact Name, Job Title, Email, LinkedIn, Status, Date, Notes, Apollo ID
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple


# --- Companies sheet ---

COMPANY_COLUMNS = ["#", "Country", "Company", "Company Domain", "Business Domain", "Apollo ID"]


@dataclass
class Company:
    row_num: int | None = None
    country: str | None = None
    company: str | None = None
    company_domain: str | None = None
    business_domain: str | None = None  # industry/vertical from Apollo
    apollo_id: str | None = None

    @classmethod
    def from_excel_row(cls, row: dict[str, object]) -> Company:
        return cls(
            row_num=_int_or_none(row.get("#")),
            country=_str_or_none(row.get("Country")),
            company=_str_or_none(row.get("Company")),
            company_domain=_str_or_none(row.get("Company Domain")),
            business_domain=_str_or_none(row.get("Business Domain")),
            apollo_id=_str_or_none(row.get("Apollo ID")),
        )

    def to_excel_row(self) -> dict[str, object]:
        return {
            "#": self.row_num or "",
            "Country": self.country or "",
            "Company": self.company or "",
            "Company Domain": self.company_domain or "",
            "Business Domain": self.business_domain or "",
            "Apollo ID": self.apollo_id or "",
        }

    def __str__(self) -> str:
        return f"{self.company or '?'} ({self.company_domain or 'no domain'})"


# --- Employees sheet ---

EMPLOYEE_COLUMNS = [
    "Company", "Contact Name", "Job Title", "Email",
    "LinkedIn", "Status", "Date", "Notes", "Apollo ID",
]


class EmployeeKey(NamedTuple):
    """Deduplication key: lowered (contact_name, company)."""
    contact_name: str
    company: str


@dataclass
class Employee:
    company: str | None = None
    contact_name: str | None = None
    job_title: str | None = None
    email: str | None = None
    linkedin: str | None = None
    status: str | None = None
    date: str | None = None
    notes: str | None = None
    apollo_id: str | None = None

    @property
    def key(self) -> EmployeeKey:
        return EmployeeKey(
            contact_name=(self.contact_name or "").strip().lower(),
            company=(self.company or "").strip().lower(),
        )

    @property
    def first_name(self) -> str:
        if not self.contact_name:
            return ""
        parts = self.contact_name.strip().split()
        return parts[0] if parts else ""

    @property
    def last_name(self) -> str:
        if not self.contact_name:
            return ""
        parts = self.contact_name.strip().split()
        return " ".join(parts[1:]) if len(parts) > 1 else ""

    @classmethod
    def from_excel_row(cls, row: dict[str, object]) -> Employee:
        return cls(
            company=_str_or_none(row.get("Company")),
            contact_name=_str_or_none(row.get("Contact Name")),
            job_title=_str_or_none(row.get("Job Title")),
            email=_str_or_none(row.get("Email")),
            linkedin=_str_or_none(row.get("LinkedIn")),
            status=_str_or_none(row.get("Status")),
            date=_str_or_none(row.get("Date")),
            notes=_str_or_none(row.get("Notes")),
            apollo_id=_str_or_none(row.get("Apollo ID")),
        )

    def to_excel_row(self) -> dict[str, object]:
        return {
            "Company": self.company or "",
            "Contact Name": self.contact_name or "",
            "Job Title": self.job_title or "",
            "Email": self.email or "",
            "LinkedIn": self.linkedin or "",
            "Status": self.status or "",
            "Date": self.date or "",
            "Notes": self.notes or "",
            "Apollo ID": self.apollo_id or "",
        }

    def __str__(self) -> str:
        return f"{self.contact_name or '?'} ({self.company or '?'}) [{self.status or ''}]"


# --- Helpers ---

def _str_or_none(val: object) -> str | None:
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


def _int_or_none(val: object) -> int | None:
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None
