import WorkIcon from "@mui/icons-material/Work";
import { Box, Chip, Paper, Typography } from "@mui/material";

interface Props {
  jobTitle: string;
  candidateCount: number;
  lastScored: string | null;
  biasDetected: boolean;
}

export function ActiveContextBanner({
  jobTitle,
  candidateCount,
  lastScored,
  biasDetected,
}: Props) {
  return (
    <Paper
      elevation={0}
      sx={{
        px: 2,
        py: 1,
        mx: 2,
        mt: 1,
        border: "1px solid rgba(59, 130, 246, 0.18)",
        borderLeft: "3px solid",
        borderLeftColor: "#3b82f6",
        bgcolor: "rgba(59, 130, 246, 0.08)",
        borderRadius: 1,
        display: "flex",
        alignItems: "center",
        gap: 2,
        flexWrap: "wrap",
      }}
    >
      <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
        <WorkIcon sx={{ fontSize: 14, color: "#3b82f6" }} />
        <Typography
          variant="caption"
          fontWeight={600}
          sx={{ color: "#0f172a", textTransform: "uppercase", letterSpacing: 0.5 }}
        >
          Active Context
        </Typography>
      </Box>

      <Typography variant="caption" sx={{ color: "#1f2937" }}>
        <b>Job:</b> {jobTitle}
      </Typography>

      <Typography variant="caption" sx={{ color: "#1f2937" }}>
        <b>Candidates:</b> {candidateCount}
      </Typography>

      {lastScored && (
        <Typography variant="caption" sx={{ color: "#1f2937" }}>
          <b>Scored:</b> {new Date(lastScored).toLocaleDateString()}
        </Typography>
      )}

      <Chip
        label={biasDetected ? "⚠ Bias flagged" : "✓ No bias"}
        size="small"
        color={biasDetected ? "warning" : "success"}
        variant="outlined"
        sx={{ height: 18, fontSize: "0.65rem" }}
      />
    </Paper>
  );
}
