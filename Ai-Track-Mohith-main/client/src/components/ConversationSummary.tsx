import { Box, Typography } from "@mui/material";

interface Props {
  summary: string;
}

export function ConversationSummary({ summary }: Props) {
  if (!summary) return null;
  return (
    <Box
      sx={{
        mt: 1.5,
        p: 1.5,
        backgroundColor: "#f0f4ff",
        borderRadius: 1,
        border: "1px solid #c5cae9",
      }}
    >
      <Typography
        variant="caption"
        sx={{
          color: "#3949ab",
          fontWeight: 600,
          textTransform: "uppercase",
          letterSpacing: "0.08em",
          display: "block",
          mb: 0.5,
        }}
      >
        Session Summary
      </Typography>
      <Typography
        variant="caption"
        sx={{ color: "#333", display: "block", lineHeight: 1.5 }}
      >
        {summary}
      </Typography>
    </Box>
  );
}
