import { PropsWithChildren, createContext, useContext, useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  AuthPayload,
  AuthResponse,
  AuthUser,
  fetchCurrentUser,
  login,
  logout,
  register,
} from "./api";

type AuthContextValue = {
  user: AuthUser | null;
  isBootstrapping: boolean;
  isSubmitting: boolean;
  errorMessage: string | null;
  login: (payload: AuthPayload) => Promise<void>;
  register: (payload: AuthPayload) => Promise<void>;
  logout: () => Promise<void>;
};

const AUTH_QUERY_KEY = ["auth", "me"] as const;

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function extractErrorMessage(error: unknown) {
  if (error instanceof Error) {
    return error.message;
  }

  return "Something went wrong while reaching the Airzone API.";
}

export function AuthProvider({ children }: PropsWithChildren) {
  const queryClient = useQueryClient();
  const sessionQuery = useQuery<AuthResponse | null>({
    queryKey: AUTH_QUERY_KEY,
    queryFn: async () => {
      try {
        return await fetchCurrentUser();
      } catch {
        return null;
      }
    },
  });

  const loginMutation = useMutation({
    mutationFn: login,
    onSuccess: (response) => {
      queryClient.setQueryData(AUTH_QUERY_KEY, response);
    },
  });

  const registerMutation = useMutation({
    mutationFn: register,
    onSuccess: (response) => {
      queryClient.setQueryData(AUTH_QUERY_KEY, response);
    },
  });

  const logoutMutation = useMutation({
    mutationFn: logout,
    onSuccess: () => {
      queryClient.setQueryData(AUTH_QUERY_KEY, null);
    },
  });

  const value = useMemo<AuthContextValue>(
    () => ({
      user: sessionQuery.data?.user ?? null,
      isBootstrapping: sessionQuery.isLoading,
      isSubmitting:
        loginMutation.isPending || registerMutation.isPending || logoutMutation.isPending,
      errorMessage:
        loginMutation.error || registerMutation.error || logoutMutation.error
          ? extractErrorMessage(
              loginMutation.error || registerMutation.error || logoutMutation.error,
            )
          : null,
      login: async (payload) => {
        await loginMutation.mutateAsync(payload);
      },
      register: async (payload) => {
        await registerMutation.mutateAsync(payload);
      },
      logout: async () => {
        await logoutMutation.mutateAsync();
      },
    }),
    [
      loginMutation.error,
      loginMutation.isPending,
      logoutMutation.error,
      logoutMutation.isPending,
      queryClient,
      registerMutation.error,
      registerMutation.isPending,
      sessionQuery.data,
      sessionQuery.isLoading,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }

  return context;
}

