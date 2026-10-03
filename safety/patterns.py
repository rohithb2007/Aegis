import re
import shlex
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ParsedCommand:
    raw_command: str
    executable: str
    subcommand: Optional[str] = None
    args: List[str] = field(default_factory=list)
    flags: List[str] = field(default_factory=list)
    targets: List[str] = field(default_factory=list)
    is_compound: bool = False
    sub_commands: List['ParsedCommand'] = field(default_factory=list)


class CommandParser:
    """Safe, deterministic command tokenizer and compound chain parser."""

    @staticmethod
    def split_compound(command_str: str) -> List[str]:
        """Split command chain by &&, ;, ||, or | into individual command segments."""
        if not command_str:
            return []
        # Split on &&, ||, ;, and | while handling basic command boundaries
        pattern = r"\s*(&&|\|\||;|\|)\s*"
        parts = re.split(pattern, command_str.strip())
        sub_cmds = []
        for p in parts:
            if p in ["&&", "||", ";", "|"]:
                continue
            cleaned = p.strip()
            if cleaned:
                sub_cmds.append(cleaned)
        return sub_cmds if sub_cmds else [command_str.strip()]

    def parse_single(self, cmd_str: str) -> ParsedCommand:
        """Parse a single command segment into executable, subcommand, args, flags, and targets."""
        cleaned = cmd_str.strip()
        if not cleaned:
            return ParsedCommand(raw_command="", executable="")

        # Tokenize preserving quotes where possible
        try:
            tokens = shlex.split(cleaned, posix=False)
        except ValueError:
            tokens = cleaned.split()

        if not tokens:
            return ParsedCommand(raw_command=cleaned, executable="")

        # Strip quotes from tokens
        tokens = [t.strip('"\'') for t in tokens if t.strip()]
        if not tokens:
            return ParsedCommand(raw_command=cleaned, executable="")

        exe = tokens[0].lower()
        # Strip trailing .exe or paths from executable
        if "\\" in exe or "/" in exe:
            exe = exe.replace("\\", "/").split("/")[-1]
        if exe.endswith(".exe"):
            exe = exe[:-4]

        # Unwrap wrappers like `python -c "..."` or `powershell -Command "..."`
        if exe in ["python", "py", "python3"] and len(tokens) > 2 and tokens[1] == "-c":
            inner_cmd = " ".join(tokens[2:])
            return self.parse_single(inner_cmd)
        elif exe in ["powershell", "pwsh", "cmd"]:
            # Check for -Command or /c
            for idx, tok in enumerate(tokens[1:], start=1):
                if tok.lower() in ["-command", "-c", "/c"] and idx + 1 < len(tokens):
                    inner_cmd = " ".join(tokens[idx+1:])
                    return self.parse_single(inner_cmd)

        subcommand = None
        args = []
        flags = []
        targets = []

        remaining = tokens[1:]

        # Handle subcommands for git, npm, docker, cargo, pip, etc.
        if remaining and exe in ["git", "npm", "npx", "pnpm", "yarn", "docker", "cargo", "go", "mvn", "gradle", "pip", "pip3"]:
            subcommand = remaining[0].lower()
            remaining = remaining[1:]

        for tok in remaining:
            if tok.startswith("-") or tok.startswith("/"):
                flags.append(tok)
            elif "." in tok or "/" in tok or "\\" in tok or tok.isupper() or len(tok) > 3:
                targets.append(tok)
                args.append(tok)
            else:
                args.append(tok)

        return ParsedCommand(
            raw_command=cleaned,
            executable=exe,
            subcommand=subcommand,
            args=args,
            flags=flags,
            targets=targets
        )

    def parse(self, command_str: str) -> ParsedCommand:
        """Parse a command string (single or compound)."""
        segments = self.split_compound(command_str)
        if len(segments) > 1:
            sub_parsed = [self.parse_single(seg) for seg in segments]
            first = sub_parsed[0]
            return ParsedCommand(
                raw_command=command_str,
                executable=first.executable,
                subcommand=first.subcommand,
                args=first.args,
                flags=first.flags,
                targets=first.targets,
                is_compound=True,
                sub_commands=sub_parsed
            )
        return self.parse_single(command_str)
