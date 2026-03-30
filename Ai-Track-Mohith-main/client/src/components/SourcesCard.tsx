import { Box, Paper, Typography } from "@mui/material";
import type { SourceUsed } from "../lib/hirelogic";

interface Props {
  sources: SourceUsed[];
}

export function SourcesCard({ sources }: Props) {
  if (!sources || sources.length === 0) return null;
  return (
    <Paper elevation={0} variant="outlined" sx={{ mt: 1, borderRadius: 1, overflow: "hidden", p: 1.5 }}>
      <Box sx={{ mb: 1 }}>
        <Typography
          variant="caption"
          fontWeight={700}
          sx={{ textTransform: "uppercase", letterSpacing: 0.5, color: "#666" }}
        >
          Sources Used
        </Typography>
      </Box>
      {sources.map((source, index) => (
        <Box
          key={`${source.document_id}-${index}`}
          sx={{
            display: "flex",
            alignItems: "flex-start",
            gap: 1,
            mb: 0.75,
            p: 1,
            backgroundColor: "#f8f9fa",
            borderRadius: 1,
            border: "1px solid #e0e0e0",
          }}
        >
          <Typography sx={{ fontSize: "1rem", mt: 0.1 }}>
            {source.type === "job_description"
              ? "📋"
              : source.type === "candidate_resume"
                ? "👤"
                : "📊"}
          </Typography>
          <Box sx={{ flex: 1 }}>
            <Typography
              variant="caption"
              sx={{ fontWeight: 600, color: "#333", display: "block" }}
            >
              {source.document_id}
            </Typography>
            <Typography variant="caption" sx={{ color: "#888", display: "block" }}>
              {source.sections_read.join(" · ")}
            </Typography>
          </Box>
        </Box>
      ))}
    </Paper>
  );
}
