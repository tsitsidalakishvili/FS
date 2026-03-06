import AsyncStorage from "@react-native-async-storage/async-storage";
import * as SQLite from "expo-sqlite";

import type { VotePayload } from "./types";

const PARTICIPANT_ID_KEY = "delib_participant_id_v1";

type QueueVote = VotePayload & {
  queue_key: string;
  queued_at: string;
};

let dbPromise: Promise<SQLite.SQLiteDatabase> | null = null;

function getDb() {
  if (!dbPromise) {
    dbPromise = SQLite.openDatabaseAsync("deliberation_mobile.db");
  }
  return dbPromise;
}

export async function initVoteQueue() {
  const db = await getDb();
  await db.execAsync(`
    CREATE TABLE IF NOT EXISTS vote_queue (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      queue_key TEXT NOT NULL UNIQUE,
      conversation_id TEXT NOT NULL,
      comment_id TEXT NOT NULL,
      choice INTEGER NOT NULL,
      queued_at TEXT NOT NULL
    );
  `);
}

export async function getOrCreateParticipantId(): Promise<string> {
  const existing = await AsyncStorage.getItem(PARTICIPANT_ID_KEY);
  if (existing) {
    return existing;
  }
  const generated = `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
  await AsyncStorage.setItem(PARTICIPANT_ID_KEY, generated);
  return generated;
}

export async function enqueueVote(vote: VotePayload): Promise<void> {
  const db = await getDb();
  const queueKey = `${vote.conversation_id}:${vote.comment_id}`;
  await db.runAsync(
    `
    INSERT INTO vote_queue (queue_key, conversation_id, comment_id, choice, queued_at)
    VALUES (?, ?, ?, ?, ?)
    ON CONFLICT(queue_key) DO UPDATE SET
      choice = excluded.choice,
      queued_at = excluded.queued_at
    `,
    [queueKey, vote.conversation_id, vote.comment_id, vote.choice, new Date().toISOString()]
  );
}

export async function listQueuedVotes(): Promise<QueueVote[]> {
  const db = await getDb();
  const rows = await db.getAllAsync<{
    queue_key: string;
    conversation_id: string;
    comment_id: string;
    choice: number;
    queued_at: string;
  }>(
    `SELECT queue_key, conversation_id, comment_id, choice, queued_at FROM vote_queue ORDER BY queued_at ASC`
  );
  return rows.map((row) => ({
    queue_key: row.queue_key,
    conversation_id: row.conversation_id,
    comment_id: row.comment_id,
    choice: Math.max(-1, Math.min(1, row.choice)) as VotePayload["choice"],
    queued_at: row.queued_at,
  }));
}

export async function removeQueuedVote(queueKey: string): Promise<void> {
  const db = await getDb();
  await db.runAsync(`DELETE FROM vote_queue WHERE queue_key = ?`, [queueKey]);
}
