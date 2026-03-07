import { Button } from "@/components/ui/button";

type Props = {
  disabled?: boolean;
  onVote: (choice: -1 | 0 | 1) => void;
};

export function VoteButtonGroup({ disabled, onVote }: Props) {
  return (
    <div className="flex flex-wrap gap-2">
      <Button
        type="button"
        variant="secondary"
        disabled={disabled}
        onClick={() => onVote(1)}
        aria-label="Vote agree"
      >
        Agree
      </Button>
      <Button
        type="button"
        variant="secondary"
        disabled={disabled}
        onClick={() => onVote(-1)}
        aria-label="Vote disagree"
      >
        Disagree
      </Button>
      <Button
        type="button"
        variant="secondary"
        disabled={disabled}
        onClick={() => onVote(0)}
        aria-label="Vote pass"
      >
        Pass
      </Button>
    </div>
  );
}
