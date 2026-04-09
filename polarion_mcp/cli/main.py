"""
polarion_mcp CLI — entry point for all polarion_mcp operations.

Every MCP tool is exposed as a subcommand. The CLI calls the tool function
directly so output format and logic stay in one place.

Usage
-----
  mcp-polarion health
  mcp-polarion projects
  mcp-polarion project        --project <alias>
  mcp-polarion project-types  --project <alias>
  mcp-polarion named-queries  --project <alias>
  mcp-polarion discover-types --project <alias> [--limit N]
  mcp-polarion get            <WORKITEM-ID>  [--project <alias>]
  mcp-polarion search         <QUERY>        --project <alias> [--fields f1,f2]
  mcp-polarion test-runs      --project <alias>
  mcp-polarion test-run       <TEST-RUN-ID>  --project <alias>
  mcp-polarion documents      --project <alias>
  mcp-polarion test-specs     <DOCUMENT-ID>  --project <alias>
  mcp-polarion plans          --project <alias>
  mcp-polarion plan           <PLAN-ID>      --project <alias>
  mcp-polarion plan-workitems <PLAN-ID>      --project <alias>
  mcp-polarion search-plans   [<QUERY>]      --project <alias>
  mcp-polarion serve          [--mode http|stdio] [--host H] [--port P]
  mcp-polarion docgen         [--variant full|simple|all] [--output PATH]
  mcp-polarion generate-openapi [--output PATH]
"""

from __future__ import annotations

import argparse
import asyncio
import sys


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(coro):
    """Run an async tool function and print its result."""
    print(asyncio.run(coro))


def _resolve_project(workitem_id: str, explicit_project: str | None) -> str:
    """Return a project alias/ID for *workitem_id*, or exit with an error."""
    if explicit_project:
        return explicit_project

    from polarion_mcp.core.settings import config_manager

    prefix = workitem_id.split("-")[0] if "-" in workitem_id else ""
    for proj in config_manager.list_projects():
        if proj["id"] == prefix or proj["alias"].upper() == prefix.upper():
            return proj["alias"]

    print(
        f"Cannot infer project for '{workitem_id}'. "
        "Please specify --project <alias>.",
        file=sys.stderr,
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# Tool subcommands
# ---------------------------------------------------------------------------


def _cmd_health(_args: argparse.Namespace) -> None:
    from polarion_mcp.mcp.tools import health_check
    _run(health_check.fn())


def _cmd_projects(_args: argparse.Namespace) -> None:
    from polarion_mcp.mcp.tools import list_projects
    _run(list_projects.fn())


def _cmd_project(args: argparse.Namespace) -> None:
    from polarion_mcp.mcp.tools import get_project_info
    _run(get_project_info.fn(args.project))


def _cmd_project_types(args: argparse.Namespace) -> None:
    from polarion_mcp.mcp.tools import get_project_types
    _run(get_project_types.fn(args.project))


def _cmd_named_queries(args: argparse.Namespace) -> None:
    from polarion_mcp.mcp.tools import get_named_queries
    _run(get_named_queries.fn(args.project))


def _cmd_discover_types(args: argparse.Namespace) -> None:
    from polarion_mcp.mcp.tools import discover_work_item_types
    _run(discover_work_item_types.fn(args.project, args.limit))


def _cmd_get(args: argparse.Namespace) -> None:
    from polarion_mcp.mcp.tools import get_workitem
    project = _resolve_project(args.workitem_id, args.project)
    _run(get_workitem.fn(project, args.workitem_id))


def _cmd_search(args: argparse.Namespace) -> None:
    from polarion_mcp.mcp.tools import search_workitems
    _run(search_workitems.fn(args.project, args.query, args.fields or None))


def _cmd_test_runs(args: argparse.Namespace) -> None:
    from polarion_mcp.mcp.tools import get_test_runs
    _run(get_test_runs.fn(args.project))


def _cmd_test_run(args: argparse.Namespace) -> None:
    from polarion_mcp.mcp.tools import get_test_run
    _run(get_test_run.fn(args.project, args.test_run_id))


def _cmd_documents(args: argparse.Namespace) -> None:
    from polarion_mcp.mcp.tools import get_documents
    _run(get_documents.fn(args.project))


def _cmd_test_specs(args: argparse.Namespace) -> None:
    from polarion_mcp.mcp.tools import get_test_specs_from_document
    _run(get_test_specs_from_document.fn(args.project, args.document_id))


def _cmd_plans(args: argparse.Namespace) -> None:
    from polarion_mcp.mcp.tools import get_plans
    _run(get_plans.fn(args.project))


def _cmd_plan(args: argparse.Namespace) -> None:
    from polarion_mcp.mcp.tools import get_plan
    _run(get_plan.fn(args.project, args.plan_id))


def _cmd_plan_workitems(args: argparse.Namespace) -> None:
    from polarion_mcp.mcp.tools import get_plan_workitems
    _run(get_plan_workitems.fn(args.project, args.plan_id))


def _cmd_search_plans(args: argparse.Namespace) -> None:
    from polarion_mcp.mcp.tools import search_plans
    _run(search_plans.fn(args.project, args.query or ""))


# ---------------------------------------------------------------------------
# Non-tool subcommands
# ---------------------------------------------------------------------------


def _cmd_serve(args: argparse.Namespace) -> None:
    if args.mode == "stdio":
        from polarion_mcp.mcp.tools import mcp
        mcp.run(transport="stdio")
    else:
        from polarion_mcp.mcp.server import run
        run(host=args.host, port=args.port, log_level=args.log_level)


def _cmd_docgen(args: argparse.Namespace) -> None:
    from pathlib import Path
    from polarion_mcp.docgen.generator import write_variant

    output = Path(args.output) if args.output else None
    if args.variant == "all":
        if output:
            print("--output cannot be used with --variant all", file=sys.stderr)
            sys.exit(1)
        for v in ("full", "simple"):
            print(f"Wrote {write_variant(v)}")  # type: ignore[arg-type]
    else:
        print(f"Wrote {write_variant(args.variant, output)}")  # type: ignore[arg-type]


def _cmd_generate_openapi(args: argparse.Namespace) -> None:
    from pathlib import Path
    from polarion_mcp.gpt_actions.generate_spec import generate_spec

    path = generate_spec(Path(args.output) if args.output else None)
    print(f"Wrote OpenAPI spec to {path}")


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

_P = "-p/--project"  # shorthand used in help strings


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mcp-polarion",
        description="Polarion MCP — CLI and server for Polarion ALM.",
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    def project_arg(p: argparse.ArgumentParser, required: bool = True) -> None:
        p.add_argument("--project", "-p", required=required, metavar="ALIAS",
                       help="Project alias or Polarion ID.")

    # ---- no-project tools ---------------------------------------------------
    sub.add_parser("health", help="Check Polarion connectivity.")
    sub.add_parser("projects", help="List configured project aliases.")

    # ---- single-project tools -----------------------------------------------
    p_project = sub.add_parser("project", help="Get project name and description.")
    project_arg(p_project)

    p_pt = sub.add_parser("project-types", help="Show configured work item types.")
    project_arg(p_pt)

    p_nq = sub.add_parser("named-queries", help="List named queries for a project.")
    project_arg(p_nq)

    p_dt = sub.add_parser("discover-types", help="Discover work item types by sampling.")
    project_arg(p_dt)
    p_dt.add_argument("--limit", "-n", type=int, default=1000, metavar="N",
                      help="Max items to sample (default: 1000).")

    p_trs = sub.add_parser("test-runs", help="List test runs.")
    project_arg(p_trs)

    p_docs = sub.add_parser("documents", help="List documents.")
    project_arg(p_docs)

    p_plans = sub.add_parser("plans", help="List plans (plan projects only).")
    project_arg(p_plans)

    # ---- project + ID tools -------------------------------------------------
    p_get = sub.add_parser("get", help="Get a work item by ID.")
    p_get.add_argument("workitem_id", metavar="WORKITEM-ID", help="e.g. ADC-1234")
    project_arg(p_get, required=False)  # can be inferred from ID prefix

    p_tr = sub.add_parser("test-run", help="Get test run details.")
    p_tr.add_argument("test_run_id", metavar="TEST-RUN-ID")
    project_arg(p_tr)

    p_ts = sub.add_parser("test-specs", help="Extract test spec IDs from a document.")
    p_ts.add_argument("document_id", metavar="DOCUMENT-ID", help="e.g. QA/TestSpecs")
    project_arg(p_ts)

    p_plan = sub.add_parser("plan", help="Get plan details.")
    p_plan.add_argument("plan_id", metavar="PLAN-ID", help="e.g. R2024.4")
    project_arg(p_plan)

    p_pwi = sub.add_parser("plan-workitems", help="Get work items in a plan.")
    p_pwi.add_argument("plan_id", metavar="PLAN-ID")
    project_arg(p_pwi)

    # ---- search tools -------------------------------------------------------
    p_search = sub.add_parser("search", help="Search work items.")
    p_search.add_argument("query", metavar="QUERY",
                          help='Lucene query or named query, e.g. "type:defect" or "query:open_bugs".')
    project_arg(p_search)
    p_search.add_argument("--fields", "-f", metavar="FIELDS",
                          help='Comma-separated fields, e.g. "id,title,status,customFields.severity".')

    p_sp = sub.add_parser("search-plans", help="Search plans (plan projects only).")
    p_sp.add_argument("query", metavar="QUERY", nargs="?", default="",
                      help='Lucene query, e.g. "templateId:release". Omit to list all.')
    project_arg(p_sp)

    # ---- serve / utilities --------------------------------------------------
    p_serve = sub.add_parser("serve", help="Start the MCP + GPT Actions server.")
    p_serve.add_argument("--mode", choices=["http", "stdio"], default="http",
                         help="http (default): MCP + GPT Actions over HTTP; stdio: MCP over stdio.")
    p_serve.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0).")
    p_serve.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000).")
    p_serve.add_argument("--log-level", default="INFO",
                         choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])

    p_docgen = sub.add_parser("docgen", help="Generate agent instruction docs.")
    p_docgen.add_argument("--variant", choices=["full", "simple", "all"], default="all")
    p_docgen.add_argument("--output", metavar="PATH")

    p_openapi = sub.add_parser("generate-openapi", help="Generate the OpenAPI spec for GPT Actions.")
    p_openapi.add_argument("--output", metavar="PATH")

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    dispatch = {
        "health":           _cmd_health,
        "projects":         _cmd_projects,
        "project":          _cmd_project,
        "project-types":    _cmd_project_types,
        "named-queries":    _cmd_named_queries,
        "discover-types":   _cmd_discover_types,
        "get":              _cmd_get,
        "search":           _cmd_search,
        "test-runs":        _cmd_test_runs,
        "test-run":         _cmd_test_run,
        "documents":        _cmd_documents,
        "test-specs":       _cmd_test_specs,
        "plans":            _cmd_plans,
        "plan":             _cmd_plan,
        "plan-workitems":   _cmd_plan_workitems,
        "search-plans":     _cmd_search_plans,
        "serve":            _cmd_serve,
        "docgen":           _cmd_docgen,
        "generate-openapi": _cmd_generate_openapi,
    }

    dispatch[args.command](args)


if __name__ == "__main__":
    main()