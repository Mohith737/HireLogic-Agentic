import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  createSession,
  fetchMessages,
  fetchSessions,
  sendMessage,
} from "../../lib/hirelogic";

export function useHireLogicSessions() {
  return useQuery({
    queryKey: ["hirelogic-sessions"],
    queryFn: fetchSessions,
  });
}

export function useSessionMessages(sessionId: number | null) {
  return useQuery({
    queryKey: ["hirelogic-messages", sessionId],
    queryFn: () => fetchMessages(sessionId!),
    enabled: sessionId !== null,
  });
}

export function useSendMessage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      question,
      job_id,
      session_id,
    }: {
      question: string;
      job_id: number | null;
      session_id: number;
    }) => sendMessage(question, job_id, session_id),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["hirelogic-messages", variables.session_id],
      });
      queryClient.invalidateQueries({
        queryKey: ["hirelogic-sessions"],
      });
    },
  });
}

export function useCreateSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      job_id,
      title,
    }: {
      job_id: number | null;
      title: string;
    }) => createSession(job_id, title),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["hirelogic-sessions"],
      });
    },
  });
}
