import { fireEvent, render, screen } from "@testing-library/react";

import { VoteButtonGroup } from "@/components/vote-button-group";

describe("VoteButtonGroup", () => {
  it("emits vote choices from buttons", () => {
    const onVote = vi.fn();
    render(<VoteButtonGroup onVote={onVote} />);

    fireEvent.click(screen.getByRole("button", { name: "Vote agree" }));
    fireEvent.click(screen.getByRole("button", { name: "Vote disagree" }));
    fireEvent.click(screen.getByRole("button", { name: "Vote pass" }));

    expect(onVote).toHaveBeenNthCalledWith(1, 1);
    expect(onVote).toHaveBeenNthCalledWith(2, -1);
    expect(onVote).toHaveBeenNthCalledWith(3, 0);
  });
});
