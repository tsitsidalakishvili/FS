import { ApiError, apiClient } from "@/lib/api/client";

describe("apiClient contracts", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("parses listConversations response with contract types", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify([
          {
            id: "c1",
            topic: "Topic",
            description: "Desc",
            is_open: true,
            allow_comment_submission: true,
            allow_viz: true,
            moderation_required: false,
            created_at: "2026-03-07T12:00:00Z",
            comments: 4,
            participants: 3,
          },
        ]),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );

    const result = await apiClient.listConversations();
    expect(result[0].id).toBe("c1");
    expect(result[0].topic).toBe("Topic");
  });

  it("throws when backend response does not match schema", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify([{ broken: true }]), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );

    await expect(apiClient.listConversations()).rejects.toBeInstanceOf(ApiError);
  });

  it("surfaces backend errors as ApiError", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Conversation not found" }), {
        status: 404,
        headers: { "content-type": "application/json" },
      }),
    );

    await expect(apiClient.getConversation("missing")).rejects.toMatchObject({
      status: 404,
      message: "Conversation not found",
    });
  });
});
