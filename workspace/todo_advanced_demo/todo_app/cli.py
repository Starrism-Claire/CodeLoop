"""Command-line interface for the Todo application."""

import argparse
import sys
from typing import List, Optional

from .manager import TaskManager
from .storage import Storage
from .utils import validate_date, parse_tags, format_task_table


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="todo",
        description="A command-line Todo management application.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  todo add "Buy groceries" -p high -d 2025-01-15 --tags "shopping,errands"
  todo list --project work --status pending --sort priority
  todo complete abc12345
  todo update abc12345 --title "New title" --priority urgent
  todo delete abc12345
  todo stats
        """,
    )

    parser.add_argument(
        "--storage", "-s",
        help="Path to the storage file (default: ~/.todo_app/tasks.json)",
        default=None,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- ADD command ---
    add_parser = subparsers.add_parser("add", help="Add a new task")
    add_parser.add_argument("title", help="Task title")
    add_parser.add_argument("-d", "--description", default="", help="Task description")
    add_parser.add_argument("-p", "--priority", default="medium",
                           help="Priority: low, medium, high, urgent (default: medium)")
    add_parser.add_argument("--due", "-D", default=None, help="Due date (YYYY-MM-DD)")
    add_parser.add_argument("--tags", "-t", default=None, help="Comma-separated tags")
    add_parser.add_argument("--project", default="default", help="Project name (default: default)")

    # --- LIST command ---
    list_parser = subparsers.add_parser("list", help="List tasks")
    list_parser.add_argument("--project", default=None, help="Filter by project")
    list_parser.add_argument("--status", default=None, help="Filter by status: pending, in_progress, completed")
    list_parser.add_argument("--priority", default=None, help="Filter by priority: low, medium, high, urgent")
    list_parser.add_argument("--tag", default=None, help="Filter by tag")
    list_parser.add_argument("--sort", default=None, help="Sort by: due_date, priority, created (add _desc for descending)")
    list_parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed task info")

    # --- SHOW command ---
    show_parser = subparsers.add_parser("show", help="Show details of a specific task")
    show_parser.add_argument("id", help="Task ID")

    # --- UPDATE command ---
    update_parser = subparsers.add_parser("update", help="Update an existing task")
    update_parser.add_argument("id", help="Task ID")
    update_parser.add_argument("--title", default=None, help="New title")
    update_parser.add_argument("-d", "--description", default=None, help="New description")
    update_parser.add_argument("-p", "--priority", default=None, help="New priority")
    update_parser.add_argument("--due", default=None, help="New due date (YYYY-MM-DD)")
    update_parser.add_argument("--tags", "-t", default=None, help="New tags (comma-separated)")
    update_parser.add_argument("--project", default=None, help="New project name")
    update_parser.add_argument("--status", default=None, help="New status")

    # --- COMPLETE command ---
    complete_parser = subparsers.add_parser("complete", help="Mark a task as completed")
    complete_parser.add_argument("id", help="Task ID")

    # --- DELETE command ---
    delete_parser = subparsers.add_parser("delete", help="Delete a task")
    delete_parser.add_argument("id", help="Task ID")

    # --- STATS command ---
    subparsers.add_parser("stats", help="Show task statistics")

    # --- PROJECTS command ---
    subparsers.add_parser("projects", help="List all projects")

    # --- TAGS command ---
    subparsers.add_parser("tags", help="List all tags")

    return parser


def run(args: Optional[List[str]] = None, storage_path: Optional[str] = None) -> int:
    """Run the CLI application.
    
    Args:
        args: Command-line arguments (defaults to sys.argv[1:])
        storage_path: Override storage file path
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = create_parser()
    parsed = parser.parse_args(args)

    if not parsed.command:
        parser.print_help()
        return 0

    # Initialize storage and manager
    storage = Storage(filepath=storage_path or parsed.storage)
    manager = TaskManager(storage)

    try:
        if parsed.command == "add":
            return _handle_add(manager, parsed)
        elif parsed.command == "list":
            return _handle_list(manager, parsed)
        elif parsed.command == "show":
            return _handle_show(manager, parsed)
        elif parsed.command == "update":
            return _handle_update(manager, parsed)
        elif parsed.command == "complete":
            return _handle_complete(manager, parsed)
        elif parsed.command == "delete":
            return _handle_delete(manager, parsed)
        elif parsed.command == "stats":
            return _handle_stats(manager)
        elif parsed.command == "projects":
            return _handle_projects(manager)
        elif parsed.command == "tags":
            return _handle_tags(manager)
        else:
            parser.print_help()
            return 0

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


def _handle_add(manager: TaskManager, args) -> int:
    """Handle the 'add' command."""
    due_date = None
    if args.due:
        due_date = validate_date(args.due)

    tags = parse_tags(args.tags)

    task = manager.add_task(
        title=args.title,
        description=args.description,
        priority=args.priority,
        due_date=due_date,
        tags=tags,
        project=args.project,
    )
    print(f"✓ Task created: [{task.id}] {task.title}")
    return 0


def _handle_list(manager: TaskManager, args) -> int:
    """Handle the 'list' command."""
    tasks = manager.list_tasks(
        project=args.project,
        status=args.status,
        priority=args.priority,
        tag=args.tag,
        sort_by=args.sort,
    )

    if args.verbose:
        if not tasks:
            print("No tasks found.")
            return 0
        for task in tasks:
            print(task)
            print()
        print(f"Total: {len(tasks)} task(s)")
    else:
        print(format_task_table(tasks))

    return 0


def _handle_show(manager: TaskManager, args) -> int:
    """Handle the 'show' command."""
    task = manager.get_task(args.id)
    print(task)
    return 0


def _handle_update(manager: TaskManager, args) -> int:
    """Handle the 'update' command."""
    updates = {}

    if args.title is not None:
        updates["title"] = args.title
    if args.description is not None:
        updates["description"] = args.description
    if args.priority is not None:
        updates["priority"] = args.priority
    if args.due is not None:
        updates["due_date"] = validate_date(args.due)
    if args.tags is not None:
        updates["tags"] = parse_tags(args.tags)
    if args.project is not None:
        updates["project"] = args.project
    if args.status is not None:
        updates["status"] = args.status

    if not updates:
        print("No updates specified. Use --help to see available options.")
        return 0

    task = manager.update_task(args.id, **updates)
    print(f"✓ Task updated: [{task.id}] {task.title}")
    return 0


def _handle_complete(manager: TaskManager, args) -> int:
    """Handle the 'complete' command."""
    task = manager.complete_task(args.id)
    print(f"✓ Task completed: [{task.id}] {task.title}")
    return 0


def _handle_delete(manager: TaskManager, args) -> int:
    """Handle the 'delete' command."""
    task = manager.delete_task(args.id)
    print(f"✓ Task deleted: [{task.id}] {task.title}")
    return 0


def _handle_stats(manager: TaskManager) -> int:
    """Handle the 'stats' command."""
    stats = manager.get_stats()
    
    print("=== Task Statistics ===")
    print(f"Total tasks: {stats['total']}")
    print(f"Overdue: {stats['overdue']}")
    print()
    
    print("By Status:")
    for status, count in stats["by_status"].items():
        print(f"  {status}: {count}")
    print()
    
    print("By Priority:")
    for priority, count in stats["by_priority"].items():
        print(f"  {priority}: {count}")
    print()
    
    if stats["projects"]:
        print(f"Projects: {', '.join(stats['projects'])}")
    
    return 0


def _handle_projects(manager: TaskManager) -> int:
    """Handle the 'projects' command."""
    projects = manager.get_projects()
    if not projects:
        print("No projects found.")
    else:
        print("Projects:")
        for p in projects:
            count = len(manager.list_tasks(project=p))
            print(f"  {p} ({count} task(s))")
    return 0


def _handle_tags(manager: TaskManager) -> int:
    """Handle the 'tags' command."""
    tags = manager.get_all_tags()
    if not tags:
        print("No tags found.")
    else:
        print("Tags:")
        for tag in tags:
            count = len(manager.list_tasks(tag=tag))
            print(f"  {tag} ({count} task(s))")
    return 0
