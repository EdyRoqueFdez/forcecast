import { create } from 'zustand';
import * as votingApi from '../api/voting';
import { Ranking, VoteRequest } from '../api/types';

interface VotingState {
  rankings: Ranking[];
  currentCategory: string;
  isLoading: boolean;
  error: string | null;
  votesCount: number;
  fetchRankings: (category: string) => Promise<void>;
  castVote: (data: VoteRequest) => Promise<void>;
  setCurrentCategory: (category: string) => void;
  incrementVotesCount: () => void;
  clearError: () => void;
}

export const useVotingStore = create<VotingState>((set) => ({
  rankings: [],
  currentCategory: 'general',
  isLoading: false,
  error: null,
  votesCount: 0,

  fetchRankings: async (category: string) => {
    set({ isLoading: true, error: null, currentCategory: category });
    try {
      const response = await votingApi.getRankings(category);
      set({ rankings: response.rankings, isLoading: false });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to fetch rankings';
      set({ error: message, isLoading: false });
    }
  },

  castVote: async (data: VoteRequest) => {
    set({ isLoading: true, error: null });
    try {
      await votingApi.createVote(data);
      set((state) => ({ votesCount: state.votesCount + 1, isLoading: false }));
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to cast vote';
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  setCurrentCategory: (category) => set({ currentCategory: category }),
  incrementVotesCount: () => set((state) => ({ votesCount: state.votesCount + 1 })),
  clearError: () => set({ error: null }),
}));
