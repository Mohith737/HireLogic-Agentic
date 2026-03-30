import AddIcon from "@mui/icons-material/Add";
import SendIcon from "@mui/icons-material/Send";
import {
  Box,
  Button,
  Chip,
  CircularProgress,
  Divider,
  IconButton,
  Paper,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import { useEffect, useMemo, useRef, useState } from "react";
import { ActiveContextBanner } from "../components/ActiveContextBanner";
import { ChatMessage } from "../components/ChatMessage";
import { SessionCard } from "../components/SessionCard";
import {
  useCreateSession,
  useHireLogicSessions,
  useSendMessage,
  useSessionMessages,
} from "../data/queries/useHireLogic";
import type {
  CandidateScorecard,
  ChatMessage as ChatMessageType,
  ScorecardPayload,
} from "../lib/hirelogic";

const SIDEBAR_WIDTH = 260;
const EXAMPLE_QUERIES = [
  "Rank all candidates for Senior ML Engineer",
  "Are there bias patterns in scoring?",
  "Compare the top 2 candidates",
  "Re-rank with Python weight at 40%",
];

type ScorecardEntry = [string, CandidateScorecard];

function isCandidateScorecard(value: unknown): value is CandidateScorecard {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Partial<CandidateScorecard>;
  return (
    typeof candidate.overall_score === "number" &&
    typeof candidate.rank === "number" &&
    typeof candidate.competency_scores === "object"
  );
}

export function HireLogicContainer() {
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null);
  const [input, setInput] = useState("");
  const [optimisticMessages, setOptimisticMessages] = useState<ChatMessageType[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  const sessions = useHireLogicSessions();
  const messages = useSessionMessages(activeSessionId);
  const sendMessage = useSendMessage();
  const createSession = useCreateSession();

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.data, optimisticMessages]);

  useEffect(() => {
    if (sessions.data?.length && activeSessionId === null) {
      setActiveSessionId(sessions.data[0].id);
      setOptimisticMessages([]);
    }
  }, [sessions.data, activeSessionId]);

  const realIds = new Set((messages.data ?? []).map((message) => message.id));
  const allMessages = [
    ...(messages.data ?? []),
    ...optimisticMessages.filter((message) => !realIds.has(message.id as number)),
  ];
  const activeSession =
    sessions.data?.find((session) => session.id === activeSessionId) ?? null;
  const assistantMessages = allMessages.filter((message) => message.role === "assistant");
  const lastAssistantMsg =
    assistantMessages.length > 0
      ? assistantMessages[assistantMessages.length - 1]
      : undefined;

  const activeContext = useMemo(() => {
    if (!lastAssistantMsg?.scorecard) return null;
    const scorecardEntries = Object.entries(
      lastAssistantMsg.scorecard as ScorecardPayload,
    ).filter(
      (entry): entry is ScorecardEntry =>
        entry[0] !== "_meta" && isCandidateScorecard(entry[1]),
    );
    if (scorecardEntries.length === 0) return null;
    const sorted = [...scorecardEntries].sort((a, b) => a[1].rank - b[1].rank);
    const top = sorted[0];
    const biasFlags = lastAssistantMsg.bias_flags?.flags ?? [];
    return {
      jobTitle:
        activeSession?.job_id === 1
          ? "Senior ML Engineer"
          : activeSession?.job_id === 2
            ? "Backend Software Engineer"
            : "Not specified",
      candidateCount: scorecardEntries.length,
      lastScored: lastAssistantMsg.created_at,
      biasDetected: biasFlags.length > 0,
      topCandidate: top?.[0] ?? "",
      topScore: top?.[1].overall_score ?? 0,
    };
  }, [activeSession, lastAssistantMsg]);

  const enrichedSessions = useMemo(
    () =>
      (sessions.data ?? []).map((session) => ({
        ...session,
        jobTitle:
          session.job_id === 1
            ? "Senior ML Engineer"
            : session.job_id === 2
              ? "Backend Software Engineer"
              : undefined,
      })),
    [sessions.data],
  );

  async function handleNewSession() {
    const result = await createSession.mutateAsync({
      job_id: null,
      title: "New Session",
    });
    setActiveSessionId(result.id);
    setOptimisticMessages([]);
  }

  async function handleSend() {
    const question = input.trim();
    if (!question || !activeSessionId) {
      return;
    }
    setInput("");

    const tempUserMessage: ChatMessageType = {
      id: Date.now(),
      role: "user",
      content: question,
      scorecard: null,
      bias_flags: null,
      created_at: new Date().toISOString(),
    };
    setOptimisticMessages((prev) => [...prev, tempUserMessage]);

    try {
      const result = await sendMessage.mutateAsync({
        question,
        job_id: null,
        session_id: activeSessionId,
      });
      const assistantMessage: ChatMessageType = {
        id: Date.now() + 1,
        role: "assistant",
        content: result.answer,
        scorecard: result.scorecard
          ? {
              ...result.scorecard,
              _meta: {
                sources_used: result.sources_used ?? [],
                conversation_summary: result.updated_conversation_summary ?? "",
              },
            }
          : null,
        bias_flags: result.bias_flags.length ? { flags: result.bias_flags } : null,
        created_at: new Date().toISOString(),
      };
      setOptimisticMessages((prev) => [...prev, assistantMessage]);
      setOptimisticMessages([]);
    } catch {
      setOptimisticMessages((prev) =>
        prev.filter((message) => message.id !== tempUserMessage.id),
      );
    }
  }

  return (
    <Box
      sx={{
        display: "flex",
        height: "calc(100vh - 64px)",
        overflow: "hidden",
        bgcolor: "#f8f9fa",
      }}
    >
      <Box
        sx={{
          width: SIDEBAR_WIDTH,
          flexShrink: 0,
          borderRight: "1px solid",
          borderColor: "divider",
          display: "flex",
          flexDirection: "column",
          bgcolor: "#111827",
        }}
      >
        <Box
          sx={{
            p: 2,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <Typography variant="subtitle2" sx={{ color: "#FFFFFF" }}>
            Sessions
          </Typography>
          <Tooltip title="New session">
            <IconButton
              size="small"
              onClick={handleNewSession}
              disabled={createSession.isPending}
              sx={{ color: "rgba(255,255,255,0.82)" }}
            >
              <AddIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
        <Divider />
        <Box sx={{ overflow: "auto", flexGrow: 1, py: 0.5 }}>
          {enrichedSessions.map((session) => (
            <SessionCard
              key={session.id}
              session={session}
              isActive={session.id === activeSessionId}
              onClick={() => {
                setActiveSessionId(session.id);
                setOptimisticMessages([]);
              }}
            />
          ))}
          {sessions.isLoading && (
            <Box sx={{ p: 2, textAlign: "center" }}>
              <CircularProgress size={20} />
            </Box>
          )}
        </Box>
      </Box>

      <Box
        sx={{
          flexGrow: 1,
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          bgcolor: "#f8f9fa",
        }}
      >
        {activeContext && (
          <ActiveContextBanner
            jobTitle={activeContext.jobTitle}
            candidateCount={activeContext.candidateCount}
            lastScored={activeContext.lastScored}
            biasDetected={activeContext.biasDetected}
          />
        )}

        <Box
          sx={{
            flexGrow: 1,
            overflow: "auto",
            p: 2,
            bgcolor: "#FFFFFF",
            borderRadius: 2,
            mx: 2,
            mb: 2,
          }}
        >
          {!activeSessionId && (
            <Box
              sx={{
                height: "100%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                p: 3,
              }}
            >
              <Paper
                elevation={0}
                variant="outlined"
                sx={{
                  p: 4,
                  borderRadius: 3,
                  maxWidth: 480,
                  textAlign: "center",
                  bgcolor: "rgba(255,255,255,0.85)",
                  border: "1px solid rgba(255,255,255,0.6)",
                }}
              >
                <Typography variant="h5" sx={{ color: "#111827" }} mb={1}>
                  ⚖️ HireLogic Assistant
                </Typography>
                <Typography variant="body2" sx={{ color: "#4b5563" }} mb={3}>
                  Screen and rank candidates with fairness and explainability.
                </Typography>
                <Typography variant="caption" sx={{ color: "#6b7280" }} display="block" mb={1.5}>
                  TRY ASKING
                </Typography>
                <Box
                  sx={{
                    display: "flex",
                    flexWrap: "wrap",
                    gap: 1,
                    justifyContent: "center",
                    mb: 3,
                  }}
                >
                  {EXAMPLE_QUERIES.map((query) => (
                    <Chip
                      key={query}
                      label={query}
                      size="small"
                      variant="outlined"
                      onClick={async () => {
                        const session = await createSession.mutateAsync({
                          job_id: 1,
                          title: query.slice(0, 50),
                        });
                        setActiveSessionId(session.id);
                        setInput(query);
                      }}
                      sx={{ cursor: "pointer" }}
                    />
                  ))}
                </Box>
                <Button
                  variant="contained"
                  startIcon={<AddIcon />}
                  onClick={() => {
                    void handleNewSession();
                  }}
                  size="small"
                >
                  New Assessment
                </Button>
              </Paper>
            </Box>
          )}
          {allMessages.map((message) => (
            <ChatMessage key={message.id} message={message} />
          ))}
          {sendMessage.isPending && (
            <Box sx={{ display: "flex", justifyContent: "flex-start", mb: 2 }}>
              <CircularProgress size={20} />
            </Box>
          )}
          <div ref={bottomRef} />
        </Box>

        <Box
          sx={{
            p: 0,
            mx: 2,
            mb: 2,
            bgcolor: "#FFFFFF",
            display: "flex",
            gap: 1,
            alignItems: "flex-end",
            border: "1px solid #E0E0E0",
            borderRadius: "24px",
            padding: "4px 8px 4px 16px",
            boxShadow: "0 2px 8px rgba(0,0,0,0.08)",
          }}
        >
          <TextField
            fullWidth
            multiline
            maxRows={4}
            size="small"
            placeholder={
              activeSessionId
                ? "Ask about candidates, rankings, or bias checks..."
                : "Create a session to start"
            }
            value={input}
            onChange={(event) => setInput(event.target.value)}
            disabled={!activeSessionId || sendMessage.isPending}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                void handleSend();
              }
            }}
            sx={{
              "& .MuiInputBase-input": {
                color: "#111827",
              },
              "& .MuiInputBase-input::placeholder": {
                color: "#6b7280",
                opacity: 1,
              },
              "& .MuiOutlinedInput-notchedOutline": {
                borderColor: "#E0E0E0",
              },
              "& .MuiOutlinedInput-root": {
                borderRadius: 3,
                color: "#111827",
              },
            }}
          />
          <IconButton
            color="primary"
            onClick={() => {
              void handleSend();
            }}
            disabled={!input.trim() || !activeSessionId || sendMessage.isPending}
            sx={{
              bgcolor: "#3b82f6",
              color: "white",
              "&:hover": { bgcolor: "#3b82f6", filter: "brightness(0.92)" },
              "&.Mui-disabled": {
                bgcolor: "action.disabledBackground",
                color: "action.disabled",
              },
              borderRadius: "50%",
              width: 40,
              height: 40,
            }}
          >
            <SendIcon fontSize="small" />
          </IconButton>
        </Box>
      </Box>
    </Box>
  );
}
