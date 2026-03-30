import { Alert, AlertTitle, Box, Typography } from "@mui/material";
import type { BiasFlag } from "../lib/hirelogic";

interface Props {
  biasFlags: BiasFlag[];
}

export function BiasFlagCard({ biasFlags }: Props) {
  if (biasFlags.length === 0) {
    return (
      <Alert
        severity="success"
        sx={{
          mt: 1,
          backgroundColor: "#e8f5e9",
          border: "1px solid #4caf50",
          userSelect: "none",
          cursor: "default",
          "& .MuiAlert-icon": { color: "#2e7d32" },
        }}
      >
        <AlertTitle
          sx={{
            color: "#1b5e20",
            fontWeight: 700,
            fontSize: "0.875rem",
          }}
        >
          No bias detected
        </AlertTitle>
        <Typography variant="body2" sx={{ color: "#2e7d32" }}>
          All candidates scored on merit-based evidence only.
        </Typography>
      </Alert>
    );
  }

  const alertSeverity = (severity: string) => {
    if (severity === "HIGH") return "error";
    if (severity === "MEDIUM") return "warning";
    return "info";
  };

  const alertSx = (severity: string) =>
    severity === "HIGH"
      ? {
          mb: 0.75,
          backgroundColor: "#ffebee",
          border: "1px solid #c62828",
        }
      : severity === "MEDIUM"
      ? {
          mb: 0.75,
          backgroundColor: "#fff8e1",
          border: "1px solid #f9a825",
          color: "#1a1a1a",
          "& .MuiAlert-icon": { color: "#f9a825" },
        }
      : {
          mb: 0.75,
        };

  return (
    <Box sx={{ mt: 1, userSelect: "none", cursor: "default" }}>
      {biasFlags.map((flag, index) => (
        <Alert
          key={`${flag.flag_type}-${index}`}
          severity={alertSeverity(flag.severity)}
          sx={alertSx(flag.severity)}
        >
          <AlertTitle sx={{ fontWeight: 700, color: "#1a1a1a" }}>
            {flag.severity} · {flag.flag_type}
          </AlertTitle>
          <Typography variant="body2" sx={{ color: "#1a1a1a" }}>
            {flag.description}
          </Typography>
          <Typography variant="caption" sx={{ color: "#555", mt: 0.5, display: "block" }}>
            → {flag.recommendation}
          </Typography>
        </Alert>
      ))}
    </Box>
  );
}
