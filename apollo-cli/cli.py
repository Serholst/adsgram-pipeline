"""Click-based CLI for Apollo Outreach — 3-phase enrichment pipeline.

Phase 1: python cli.py domains   — enrich Companies sheet with Business Domain
Phase 2: python cli.py search    — find employees, populate Employees sheet
Phase 3: python cli.py enrich    — fill emails for employees (costs credits)
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import click


def _lazy_init(ctx: click.Context) -> None:
    """Import config/clients lazily so --help works without .env."""
    if hasattr(ctx, "_apollo_initialized"):
        return
    ctx._apollo_initialized = True  # type: ignore[attr-defined]

    import config
    from logger import setup_logging

    verbose = ctx.obj.get("verbose", False)
    setup_logging(verbose=verbose, log_file=config.LOG_FILE)

    excel_path = ctx.obj.get("excel_path") or config.EXCEL_PATH
    ctx.obj["excel_path"] = Path(excel_path)
    ctx.obj["backup_dir"] = config.BACKUP_DIR


log = logging.getLogger(__name__)


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging.")
@click.option("--excel-path", type=click.Path(), default=None, help="Path to Excel file.")
@click.pass_context
def apollo(ctx: click.Context, verbose: bool, excel_path: str | None) -> None:
    """Apollo Outreach — 3-phase enrichment pipeline."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    if excel_path:
        ctx.obj["excel_path"] = excel_path


# ─── PHASE 1: DOMAINS ─────────────────────────────────────────────────────────


@apollo.command()
@click.option("--limit", type=int, default=None, help="Max companies to enrich.")
@click.option("--dry-run", is_flag=True, help="Show what would happen without making changes.")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
@click.pass_context
def domains(ctx: click.Context, limit: int | None, dry_run: bool, yes: bool) -> None:
    """Phase 1: Enrich Companies sheet with Business Domain from Apollo.

    Calls Apollo Organization Enrichment for each company domain.
    Fills the 'Business Domain' column with the company's industry.
    Costs 1 credit per company.

    After running: review Business Domain column, delete rows with irrelevant industries.
    """
    _lazy_init(ctx)

    from config import MAX_CONSECUTIVE_ERRORS, SAVE_EVERY_N
    from excel_handler import ExcelHandler
    from apollo_client import ApolloClient

    handler = ExcelHandler(ctx.obj["excel_path"], ctx.obj["backup_dir"])
    companies = handler.read_companies()

    if not companies:
        click.echo("No companies found in Companies sheet.")
        return

    # Filter: has domain but no business domain yet
    eligible = [c for c in companies if c.company_domain and not c.business_domain]

    if not eligible:
        click.echo("All companies already have Business Domain set.")
        return

    if limit:
        eligible = eligible[-limit:]  # take from the bottom

    click.echo(f"Companies to enrich: {len(eligible)}")
    click.echo(f"Estimated credits:   {len(eligible)}")

    client = ApolloClient()
    remaining = client.credits_remaining_today()
    click.echo(f"Credits remaining:   {remaining}")

    if dry_run:
        click.echo("\n[DRY RUN] Would enrich:")
        for c in eligible:
            click.echo(f"  - {c.company} ({c.company_domain})")
        return

    try:
        client.check_credit_budget(len(eligible))
    except Exception as e:
        click.echo(f"\n{e}")
        return

    if not yes:
        if not click.confirm(f"\nProceed with enriching {len(eligible)} companies?"):
            click.echo("Aborted.")
            return

    comp_index = {id(c): i for i, c in enumerate(companies)}
    enriched_count = 0
    not_found_count = 0
    error_count = 0
    consecutive_errors = 0

    for batch_num, comp in enumerate(eligible, start=1):
        try:
            org = client.enrich_organization(comp.company_domain)
            consecutive_errors = 0
            idx = comp_index[id(comp)]

            if org:
                industry = org.get("industry") or org.get("industry_tag_id") or ""
                keywords = ", ".join(org.get("keywords", [])[:3]) if org.get("keywords") else ""
                # Use industry if available, otherwise first keywords
                biz_domain = industry or keywords or "Unknown"
                companies[idx].business_domain = biz_domain
                companies[idx].apollo_id = org.get("id", "")
                enriched_count += 1
                click.echo(f"  [{batch_num}/{len(eligible)}] {comp.company} -> {biz_domain}")
            else:
                companies[idx].business_domain = "Not Found"
                not_found_count += 1
                click.echo(f"  [{batch_num}/{len(eligible)}] {comp.company} -> not found")

        except Exception as e:
            error_count += 1
            consecutive_errors += 1
            log.error("Error enriching %s: %s", comp, e)
            click.echo(f"  [{batch_num}/{len(eligible)}] {comp.company} -> ERROR: {e}")
            if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                click.echo(f"\nAborting: {MAX_CONSECUTIVE_ERRORS} consecutive errors.")
                break

        if batch_num % SAVE_EVERY_N == 0:
            handler.write_companies(companies)
            click.echo(f"  [Progress saved at {batch_num}/{len(eligible)}]")

    handler.write_companies(companies)
    click.echo(f"\n--- Phase 1 Summary ---")
    click.echo(f"Enriched:    {enriched_count}")
    click.echo(f"Not found:   {not_found_count}")
    click.echo(f"Errors:      {error_count}")
    click.echo(f"Credits used: {enriched_count + not_found_count}")
    click.echo(f"\nNext: review 'Business Domain' column, delete irrelevant rows,")
    click.echo(f"then run: python cli.py search")


# ─── PHASE 2: SEARCH ──────────────────────────────────────────────────────────


@apollo.command()
@click.option("--titles", default=None,
              help="Comma-separated job titles. Default: built-in target roles list.")
@click.option("--max-results", type=int, default=10, help="Max results per company. Default: 10.")
@click.option("--dry-run", is_flag=True, help="Show results without writing to Excel.")
@click.pass_context
def search(ctx: click.Context, titles: str | None, max_results: int,
           dry_run: bool) -> None:
    """Phase 2: Search for employees at companies in Companies sheet.

    Searches Apollo for people matching target job titles at each company.
    Populates the Employees sheet. Search is FREE (no credits).

    After running: review Employees sheet, delete irrelevant job titles,
    then run: python cli.py enrich
    """
    _lazy_init(ctx)

    from config import TARGET_TITLES
    from models import Employee, EmployeeKey
    from excel_handler import ExcelHandler
    from apollo_client import ApolloClient

    handler = ExcelHandler(ctx.obj["excel_path"], ctx.obj["backup_dir"])
    companies = handler.read_companies()
    existing_employees = handler.read_employees()
    existing_keys = {e.key for e in existing_employees}

    # Only search companies that have a domain
    eligible = [c for c in companies if c.company_domain]

    if not eligible:
        click.echo("No companies with Company Domain found. Run Phase 1 first.")
        return

    title_list = [t.strip() for t in titles.split(",")] if titles else TARGET_TITLES

    click.echo(f"Companies to search: {len(eligible)}")
    click.echo(f"Titles: {', '.join(title_list)}")
    click.echo(f"Max results per company: {max_results}")
    click.echo(f"Search is FREE — no credits consumed.\n")

    client = ApolloClient()
    all_new: list[Employee] = []
    total_found = 0
    total_skipped = 0

    for comp in eligible:
        click.echo(f"Searching {comp.company} ({comp.company_domain})...")
        try:
            results = client.search_people(
                organization_domains=[comp.company_domain],
                person_titles=title_list,
                per_page=min(max_results, 100),
                max_pages=1,
            )
        except Exception as e:
            click.echo(f"  ERROR: {e}")
            continue

        results = results[:max_results]
        total_found += len(results)

        for person in results:
            name = f"{person.get('first_name', '')} {person.get('last_name', '')}".strip()
            emp = Employee(
                company=comp.company,
                contact_name=name,
                job_title=person.get("title"),
                linkedin=person.get("linkedin_url"),
                status="New",
                date=datetime.now().strftime("%Y-%m-%d"),
                apollo_id=person.get("id"),
            )
            if emp.key in existing_keys:
                total_skipped += 1
            else:
                all_new.append(emp)
                existing_keys.add(emp.key)
                click.echo(f"  + {name} — {emp.job_title}")

        if not results:
            click.echo("  (no results)")

    click.echo(f"\n--- Phase 2 Summary ---")
    click.echo(f"Total found:     {total_found}")
    click.echo(f"New employees:   {len(all_new)}")
    click.echo(f"Already exist:   {total_skipped}")

    if not all_new:
        click.echo("No new employees to add.")
        return

    if dry_run:
        click.echo("\n[DRY RUN] No changes written.")
        return

    all_employees = existing_employees + all_new
    handler.write_employees(all_employees)

    click.echo(f"\nAdded {len(all_new)} employees to Employees sheet.")
    click.echo(f"\nNext: review 'Job Title' column, delete irrelevant rows,")
    click.echo(f"then run: python cli.py enrich")


# ─── PHASE 3: ENRICH ──────────────────────────────────────────────────────────


@apollo.command()
@click.option("--limit", type=int, default=None, help="Max employees to enrich.")
@click.option("--dry-run", is_flag=True, help="Show what would happen without making changes.")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
@click.pass_context
def enrich(ctx: click.Context, limit: int | None, dry_run: bool, yes: bool) -> None:
    """Phase 3: Fill emails for employees in Employees sheet.

    Calls Apollo People Match for each employee without an email.
    Costs 1 credit per employee.
    """
    _lazy_init(ctx)

    from config import SAVE_EVERY_N, MAX_CONSECUTIVE_ERRORS
    from excel_handler import ExcelHandler
    from apollo_client import ApolloClient

    handler = ExcelHandler(ctx.obj["excel_path"], ctx.obj["backup_dir"])
    employees = handler.read_employees()
    companies = handler.read_companies()

    # Build domain lookup: company name -> domain
    domain_map: dict[str, str] = {}
    for c in companies:
        if c.company and c.company_domain:
            domain_map[c.company.strip().lower()] = c.company_domain

    if not employees:
        click.echo("No employees found in Employees sheet. Run Phase 2 first.")
        return

    # Filter: no email yet
    eligible = [e for e in employees if not e.email and e.contact_name]

    if limit:
        eligible = eligible[:limit]

    if not eligible:
        click.echo("All employees already have emails (or no eligible employees).")
        return

    click.echo(f"Employees to enrich: {len(eligible)}")
    click.echo(f"Estimated credits:   {len(eligible)}")

    client = ApolloClient()
    remaining = client.credits_remaining_today()
    click.echo(f"Credits remaining:   {remaining}")

    if dry_run:
        click.echo("\n[DRY RUN] Would enrich:")
        for e in eligible:
            click.echo(f"  - {e.contact_name} @ {e.company}")
        return

    try:
        client.check_credit_budget(len(eligible))
    except Exception as e:
        click.echo(f"\n{e}")
        return

    if not yes:
        if not click.confirm(f"\nProceed? This will spend {len(eligible)} credits."):
            click.echo("Aborted.")
            return

    emp_index = {id(e): i for i, e in enumerate(employees)}
    enriched_count = 0
    not_found_count = 0
    error_count = 0
    consecutive_errors = 0

    for batch_num, emp in enumerate(eligible, start=1):
        try:
            domain = domain_map.get((emp.company or "").strip().lower())

            result = client.enrich_person(
                first_name=emp.first_name,
                last_name=emp.last_name,
                domain=domain,
                organization_name=emp.company,
            )
            consecutive_errors = 0
            idx = emp_index[id(emp)]

            if result and result.get("email"):
                employees[idx].email = result["email"]
                employees[idx].status = "Enriched"
                if result.get("linkedin_url") and not employees[idx].linkedin:
                    employees[idx].linkedin = result["linkedin_url"]
                enriched_count += 1
                click.echo(f"  [{batch_num}/{len(eligible)}] {emp.contact_name} -> {result['email']}")
            else:
                employees[idx].status = "No Email"
                not_found_count += 1
                click.echo(f"  [{batch_num}/{len(eligible)}] {emp.contact_name} -> no email found")

        except Exception as e:
            error_count += 1
            consecutive_errors += 1
            log.error("Error enriching %s: %s", emp, e)
            click.echo(f"  [{batch_num}/{len(eligible)}] {emp.contact_name} -> ERROR: {e}")
            if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                click.echo(f"\nAborting: {MAX_CONSECUTIVE_ERRORS} consecutive errors.")
                break

        if batch_num % SAVE_EVERY_N == 0:
            handler.write_employees(employees)
            click.echo(f"  [Progress saved at {batch_num}/{len(eligible)}]")

    handler.write_employees(employees)
    click.echo(f"\n--- Phase 3 Summary ---")
    click.echo(f"Enriched:      {enriched_count}")
    click.echo(f"No email:      {not_found_count}")
    click.echo(f"Errors:        {error_count}")
    click.echo(f"Credits used:  {enriched_count + not_found_count}")
    click.echo(f"Credits left:  {client.credits_remaining_today()}")


# ─── STATUS ────────────────────────────────────────────────────────────────────


@apollo.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show pipeline status: companies, employees, credits."""
    _lazy_init(ctx)

    from excel_handler import ExcelHandler
    from apollo_client import ApolloClient

    handler = ExcelHandler(ctx.obj["excel_path"], ctx.obj["backup_dir"])

    companies = handler.read_companies()
    employees = handler.read_employees()

    click.echo(f"\n--- Companies ({len(companies)}) ---")
    with_domain = sum(1 for c in companies if c.company_domain)
    with_biz = sum(1 for c in companies if c.business_domain)
    click.echo(f"  With domain:          {with_domain}")
    click.echo(f"  With business domain: {with_biz}")

    click.echo(f"\n--- Employees ({len(employees)}) ---")
    status_counts: dict[str, int] = {}
    with_email = 0
    for e in employees:
        s = e.status or "(no status)"
        status_counts[s] = status_counts.get(s, 0) + 1
        if e.email:
            with_email += 1
    for s, count in sorted(status_counts.items()):
        click.echo(f"  {s:20s} {count}")
    click.echo(f"  {'with email':20s} {with_email}")

    client = ApolloClient()
    click.echo(f"\n--- Credits ---")
    click.echo(f"  Used today:      {client.credits_used_today()}")
    click.echo(f"  Remaining today: {client.credits_remaining_today()}")


if __name__ == "__main__":
    apollo()
