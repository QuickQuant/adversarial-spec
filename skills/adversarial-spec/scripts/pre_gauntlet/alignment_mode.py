"""
Alignment Mode

Interactive and non-interactive alignment flow when blockers are detected.
"""

from __future__ import annotations

import sys
from enum import Enum

from .models import (
    AlignmentIssue,
    AlignmentResolution,
    AlignmentStatus,
    Concern,
    ConcernSeverity,
    PreGauntletResult,
    PreGauntletStatus,
)


class AlignmentChoice(Enum):
    """User choice in alignment mode."""

    FIX_CODE = "f"
    UPDATE_SPEC = "u"
    IGNORE = "i"
    QUIT = "q"


# Required confirmation token for ignore
IGNORE_CONFIRMATION = "I KNOW THIS WILL BREAK"


class AlignmentModeController:
    """Controls the alignment mode flow."""

    def __init__(self, interactive: bool = True):
        """Initialize alignment mode controller.

        Args:
            interactive: If True, prompt user. If False, return NEEDS_ALIGNMENT.
        """
        self.interactive = interactive

    def handle_blockers(
        self,
        blockers: list[Concern],
        result: PreGauntletResult,
    ) -> tuple[PreGauntletStatus, list[AlignmentIssue]]:
        """Handle blocker concerns.

        Args:
            blockers: List of BLOCKER severity concerns
            result: Current pre-gauntlet result

        Returns:
            (status, alignment_issues)
        """
        if not blockers:
            return PreGauntletStatus.COMPLETE, []

        # Create alignment issues for each blocker
        issues = [
            AlignmentIssue(
                concern_id=b.id,
                status=AlignmentStatus.UNRESOLVED,
            )
            for b in blockers
        ]

        # Non-interactive mode
        if not self.interactive or not sys.stdin.isatty():
            return PreGauntletStatus.NEEDS_ALIGNMENT, issues

        # Interactive mode
        return self._interactive_flow(blockers, issues)

    def _interactive_flow(
        self,
        blockers: list[Concern],
        issues: list[AlignmentIssue],
    ) -> tuple[PreGauntletStatus, list[AlignmentIssue]]:
        """Run interactive alignment flow."""
        self._print_header()
        self._print_blockers(blockers)
        self._print_options()

        while True:
            choice = self._get_choice()

            if choice == AlignmentChoice.QUIT:
                return PreGauntletStatus.ABORTED, issues

            if choice == AlignmentChoice.FIX_CODE:
                print("\nPausing gauntlet. Fix the issues in the codebase, then re-run.")
                print("When ready, run the gauntlet again with --pre-gauntlet")
                return PreGauntletStatus.NEEDS_ALIGNMENT, issues

            if choice == AlignmentChoice.UPDATE_SPEC:
                print("\nPausing gauntlet. Update the spec to match the current codebase state.")
                print("When ready, run the gauntlet again with --pre-gauntlet")
                return PreGauntletStatus.NEEDS_ALIGNMENT, issues

            if choice == AlignmentChoice.IGNORE:
                if self._confirm_ignore():
                    # Mark all issues as overridden
                    for issue in issues:
                        issue.status = AlignmentStatus.OVERRIDDEN
                        issue.resolution = AlignmentResolution.IGNORE
                    return PreGauntletStatus.COMPLETE, issues
                # User didn't confirm, go back to menu
                self._print_options()

    def _print_header(self) -> None:
        """Print alignment mode header."""
        print("\n" + "=" * 60)
        print("ALIGNMENT MODE: Drift detected between spec and codebase")
        print("=" * 60)
        print()
        print("The following issues require resolution before proceeding:")
        print()

    def _print_blockers(self, blockers: list[Concern]) -> None:
        """Print blocker concerns."""
        for b in blockers:
            print(f"  {b.id}: {b.title} [BLOCKER]")
            # Print message indented
            for line in b.message.split("\n")[:5]:  # First 5 lines
                print(f"    {line}")
            if len(b.message.split("\n")) > 5:
                print("    ...")
            print()

    def _print_options(self) -> None:
        """Print available options."""
        print("Options:")
        print("  [f] Fix codebase - Pause gauntlet, fix the issues, then re-check")
        print("  [u] Update spec  - Edit the spec to match current codebase state")
        print("  [i] Ignore       - Force proceed (DANGEROUS - requires confirmation)")
        print("  [q] Quit         - Exit gauntlet without proceeding")
        print()

    def _get_choice(self) -> AlignmentChoice:
        """Get user's choice."""
        while True:
            try:
                choice = input("Choice [f/u/i/q]: ").strip().lower()
                if choice in ("f", "u", "i", "q"):
                    return AlignmentChoice(choice)
                print("Invalid choice. Please enter f, u, i, or q.")
            except (EOFError, KeyboardInterrupt):
                print("\nAborted.")
                return AlignmentChoice.QUIT

    def _confirm_ignore(self) -> bool:
        """Confirm ignore action with explicit token."""
        print()
        print("WARNING: Ignoring these issues may cause:")
        print("  - Implementation to fail")
        print("  - Spec to be based on incorrect assumptions")
        print("  - Wasted effort on code that won't work")
        print()
        print(f"To proceed anyway, type exactly: {IGNORE_CONFIRMATION}")
        print()

        try:
            confirmation = input("Confirmation: ").strip()
            if confirmation == IGNORE_CONFIRMATION:
                print("\nProceeding with override. alignment_override=true recorded.")
                return True
            else:
                print("\nConfirmation did not match. Returning to menu.")
                return False
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            return False


def run_alignment_mode(
    blockers: list[Concern],
    result: PreGauntletResult,
    interactive: bool = True,
) -> tuple[PreGauntletStatus, list[AlignmentIssue], bool]:
    """Run alignment mode for blocker concerns.

    Args:
        blockers: List of BLOCKER severity concerns
        result: Current pre-gauntlet result
        interactive: Whether to prompt user

    Returns:
        (status, alignment_issues, was_overridden)
    """
    controller = AlignmentModeController(interactive=interactive)
    status, issues = controller.handle_blockers(blockers, result)

    # Check if any issues were overridden
    was_overridden = any(i.status == AlignmentStatus.OVERRIDDEN for i in issues)

    return status, issues, was_overridden
