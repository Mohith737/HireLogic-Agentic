import { Box, Chip, Paper, Typography } from "@mui/material";
import type { ChatSession } from "../lib/hirelogic";

function relativeDate(dateStr: string): string {
  const d = new Date(dateStr);
  const now = new Date();
  const diff = Math.floor((now.getTime() - d.getTime()) / 86400000);
  if (diff === 0) return "Today";
  if (diff === 1) return "Yesterday";
  return d.toLocaleDateString();
}

interface Props {
  session: ChatSession & {
    topCandidate?: string;
    topScore?: number;
    candidateCount?: number;
    biasDetected?: boolean;
    jobTitle?: string;
  };
  isActive: boolean;
  onClick: () => void;
}

export function SessionCard({ session, isActive, onClick }: Props) {
  return (
    <Paper
      elevation={0}
      onClick={onClick}
      sx={{
        p: 1.5,
        mb: 0.5,
        mx: 0.5,
        cursor: "pointer",
        borderLeft: isActive ? "3px solid #90caf9" : "3px solid transparent",
        backgroundColor: isActive ? "rgba(255,255,255,0.12)" : "transparent",
        borderRadius: 1,
        "&:hover": { backgroundColor: "rgba(255,255,255,0.06)" },
        transition: "all 0.15s",
      }}
    >
      <Typography
        variant="subtitle2"
        noWrap
        sx={{
          mb: 0.25,
          color: isActive ? "#ffffff" : "rgba(255,255,255,0.88)",
          fontWeight: 600,
        }}
      >
        {session.title || "New Session"}
      </Typography>

      {session.jobTitle && (
        <Typography variant="caption" display="block" sx={{ color: "rgba(255,255,255,0.70)" }}>
          {session.jobTitle}
        </Typography>
      )}

      {session.topCandidate && (
        <Typography variant="caption" display="block" sx={{ color: "rgba(255,255,255,0.70)" }}>
          Top: {session.topCandidate}
          {session.topScore !== undefined ? ` (${session.topScore.toFixed(1)})` : ""}
          {session.candidateCount ? ` · ${session.candidateCount} candidates` : ""}
        </Typography>
      )}

      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          mt: 0.5,
        }}
      >
        <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.45)", fontSize: "0.70rem" }}>
          {relativeDate(session.created_at)}
        </Typography>
        {session.topCandidate && (
          <Chip
            label={session.biasDetected ? "⚠ Bias" : "✓ Clean"}
            size="small"
            color={session.biasDetected ? "warning" : "success"}
            variant="outlined"
            sx={{ height: 18, fontSize: "0.6rem" }}
          />
        )}
      </Box>
    </Paper>
  );
}
