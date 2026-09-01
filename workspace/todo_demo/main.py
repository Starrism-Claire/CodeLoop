import sys
from todo import TodoList

DATA_FILE = "tasks.json"


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <add|remove|complete|list> [task]")
        sys.exit(1)

    command = sys.argv[1]
    todo = TodoList()
    todo.load(DATA_FILE)

    if command == "list":
        tasks = todo.list_tasks()
        if not tasks:
            print("No tasks.")
        else:
            for task, done in tasks.items():
                status = "[x]" if done else "[ ]"
                print(f"{status} {task}")
    elif command in ("add", "remove", "complete"):
        if len(sys.argv) < 3:
            print(f"Usage: python main.py {command} <task>")
            sys.exit(1)
        task = sys.argv[2]
        if command == "add":
            todo.add(task)
            print(f"Added: {task}")
        elif command == "remove":
            todo.remove(task)
            print(f"Removed: {task}")
        elif command == "complete":
            todo.complete(task)
            print(f"Completed: {task}")
        todo.save(DATA_FILE)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
