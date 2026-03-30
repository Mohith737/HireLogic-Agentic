import { Box, Paper, Typography } from "@mui/material";
import { BiasFlagCard } from "./BiasFlagCard";
import { ConversationSummary } from "./ConversationSummary";
import { ScorecardCard } from "./ScorecardCard";
import { SourcesCard } from "./SourcesCard";
import type {
  CandidateScorecard,
  ChatMessage as ChatMessageType,
  ScorecardMeta,
  ScorecardPayload,
  SourceUsed,
} from "../lib/hirelogic";

interface Props {
  message: ChatMessageType;
}

export function ChatMessage({ message }: Props) {
  const isUser = message.role === "user";
  const payload = message.scorecard as ScorecardPayload | null;
  const meta = payload?._meta as ScorecardMeta | undefined;
  const sourcesUsed = (meta?.sources_used ?? []) as SourceUsed[];
  const summary = meta?.conversation_summary ?? "";

  const cleanScorecard = message.scorecard
    ? Object.fromEntries(
        Object.entries(message.scorecard).filter(([key]) => key !== "_meta"),
      )
    : null;

  const biasFlags = message.bias_flags?.flags ?? [];
  const ranking = cleanScorecard
    ? Object.entries(cleanScorecard)
        .map(([id, data]) => ({
          rank: (data as CandidateScorecard).rank ?? 0,
          anon_id: id,
          overall_score: (data as CandidateScorecard).overall_score ?? 0,
        }))
        .sort((a, b) => a.rank - b.rank)
    : [];
  const scorecardData = message.scorecard;
  const candidates = scorecardData
    ? Object.entries(scorecardData).filter(([key]) => key !== "_meta")
    : [];
  const hasRealScores = candidates.some(
    ([, value]) => ((value as CandidateScorecard | undefined)?.overall_score ?? 0) > 0,
  );

  return (
    <Box sx={{ display: "flex", justifyContent: isUser ? "flex-end" : "flex-start", mb: 2 }}>
      <Box sx={{ maxWidth: isUser ? "70%" : "85%", minWidth: 120 }}>
        <Paper
          elevation={0}
          sx={{
            px: 2,
            py: 2,
            bgcolor: isUser ? "#3b82f6" : "#FFFFFF",
            color: isUser ? "#FFFFFF" : "#111827",
            borderRadius: isUser ? "18px 18px 4px 18px" : "4px 18px 18px 18px",
            border: isUser ? "none" : "1px solid #E0E0E0",
            boxShadow: isUser ? "0 1px 2px rgba(0,0,0,0.15)" : "none",
          }}
        >
          <Typography variant="body2" sx={{ whiteSpace: "pre-wrap", lineHeight: 1.6 }}>
            {message.content}
          </Typography>

          {!isUser && hasRealScores ? (
            <>
              <ScorecardCard
                ranking={ranking}
                scorecard={cleanScorecard as Record<string, CandidateScorecard>}
              />
              <BiasFlagCard biasFlags={biasFlags} />
            </>
          ) : !isUser && message.scorecard !== null ? (
            <Box
              sx={{
                p: 2,
                backgroundColor: "#fff8e1",
                borderRadius: 1,
                border: "1px solid #ffe082",
                mt: 1,
              }}
            >
              <Typography variant="body2" sx={{ color: "#795548" }}>
                ⚠️ No candidates were scored for this query. Try: "Rank all candidates for
                Senior ML Engineer role"
              </Typography>
            </Box>
          ) : null}

          {!isUser && sourcesUsed.length > 0 && (
            <SourcesCard sources={sourcesUsed as SourceUsed[]} />
          )}

          {!isUser && summary && <ConversationSummary summary={summary} />}

          <Box sx={{ display: "flex", justifyContent: "flex-end", mt: 0.5 }}>
            <Typography
              variant="caption"
              sx={{ color: isUser ? "rgba(255,255,255,0.8)" : "#aaa", fontSize: "0.7rem", userSelect: "none" }}
            >
              {new Date(message.created_at).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </Typography>
          </Box>
        </Paper>
      </Box>
    </Box>
  );
}
