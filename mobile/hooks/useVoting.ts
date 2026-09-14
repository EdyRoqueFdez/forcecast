import { useVotingStore } from '../stores/votingStore';

export function useVoting() {
  const {
    rankings,
    currentCategory,
    isLoading,
    error,
    votesCount,
    fetchRankings,
    castVote,
    setCurrentCategory,
    incrementVotesCount,
    clearError,
  } = useVotingStore();

  return {
    rankings,
    currentCategory,
    isLoading,
    error,
    votesCount,
    fetchRankings,
    castVote,
    setCurrentCategory,
    incrementVotesCount,
    clearError,
  };
}
