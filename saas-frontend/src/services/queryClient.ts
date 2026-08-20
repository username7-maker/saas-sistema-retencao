import { QueryClient } from "@tanstack/react-query";


export function createAppQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 5 * 60 * 1000,
        refetchOnWindowFocus: true,
        refetchOnReconnect: true,
        retry: 2,
      },
    },
  });
}
