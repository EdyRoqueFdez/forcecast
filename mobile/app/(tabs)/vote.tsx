import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, RefreshControl } from 'react-native';
import { useTheme } from '../../hooks/useTheme';
import { useVoting } from '../../hooks/useVoting';
import { ScreenContainer } from '../../components/layout/ScreenContainer';
import { VoteCard } from '../../components/features/VoteCard';
import { CategoryPicker } from '../../components/ui/CategoryPicker';
import { SkeletonCard } from '../../components/ui/Skeleton';
import { Toast } from '../../components/ui/Toast';
import { Model } from '../../api/types';
import { getModels } from '../../api/models';
import { createVote } from '../../api/voting';
import { getCategories } from '../../api/meta';

export default function VoteScreen() {
  const { colors } = useTheme();
  const { votesCount, incrementVotesCount } = useVoting();
  const [models, setModels] = useState<Model[]>([]);
  const [currentPair, setCurrentPair] = useState<[Model, Model] | null>(null);
  const [selectedCategory, setSelectedCategory] = useState('coding');
  const [categories, setCategories] = useState([{ id: 'coding', name: 'Coding' }]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  useEffect(() => {
    getCategories()
      .then((items) => setCategories(items.map((item) => ({ id: item.slug, name: item.name }))))
      .catch(() => undefined);
    loadModels();
  }, [selectedCategory]);

  const loadModels = async () => {
    setIsLoading(true);
    try {
      const response = await getModels({ category: selectedCategory, per_page: 100 });
      setModels(response.models);
      if (response.models.length >= 2) {
        pickRandomPair(response.models);
      }
    } catch (error) {
      setToast({ message: 'Failed to load models', type: 'error' });
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  const pickRandomPair = (modelList: Model[]) => {
    const shuffled = [...modelList].sort(() => Math.random() - 0.5);
    setCurrentPair([shuffled[0], shuffled[1]]);
  };

  const handleVote = async (modelSlug: string) => {
    if (!currentPair) return;

    try {
      await createVote({
        model_slug: modelSlug,
        category_slug: selectedCategory,
        vote_type: 'upvote',
      });
      incrementVotesCount();
      setToast({ message: 'Vote recorded!', type: 'success' });
      pickRandomPair(models);
    } catch (error) {
      setToast({ message: 'Failed to record vote', type: 'error' });
    }
  };

  const handleSkip = () => {
    if (currentPair) {
      pickRandomPair(models);
    }
  };

  const onRefresh = () => {
    setIsRefreshing(true);
    loadModels();
  };

  return (
    <ScreenContainer
      scrollable
      showBrandHeader
      refreshControl={<RefreshControl refreshing={isRefreshing} onRefresh={onRefresh} />}
    >
      <View style={styles.header}>
        <Text style={[styles.kicker, { color: colors.primary }]}>DAILY SIGNAL / {Math.min(votesCount + 1, 50)} OF 50</Text>
        <Text style={[styles.title, { color: colors.text }]}>Which model is better?</Text>
        <Text style={[styles.subtitle, { color: colors.textSecondary }]}>Your signal shapes the community ranking.</Text>
      </View>

      <CategoryPicker value={selectedCategory} options={categories} onChange={setSelectedCategory} />

      <View style={styles.progressRow}>
        <Text style={[styles.progressLabel, { color: colors.textSecondary }]}>Choose the model you trust for this task.</Text>
        <Text style={[styles.progressLabel, { color: colors.textSecondary }]}>14%</Text>
      </View>
      <View style={[styles.progressTrack, { backgroundColor: colors.border }]}>
        <View style={[styles.progressFill, { backgroundColor: colors.primary }]} />
      </View>

      {isLoading ? (
        <View style={styles.loading}>
          <SkeletonCard />
          <SkeletonCard />
        </View>
      ) : currentPair ? (
        <View style={styles.cards}>
          <VoteCard model={currentPair[0]} onPress={() => handleVote(currentPair[0].slug)} />
          <View style={styles.divider}>
            <Text style={[styles.vs, { color: colors.textTertiary }]}>VS</Text>
          </View>
          <VoteCard model={currentPair[1]} onPress={() => handleVote(currentPair[1].slug)} />
        </View>
      ) : (
        <View style={styles.empty}>
          <Text style={[styles.emptyText, { color: colors.textSecondary }]}>
            No models available in this category
          </Text>
        </View>
      )}

      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onDismiss={() => setToast(null)}
        />
      )}
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  header: {
    marginBottom: 14,
  },
  kicker: {
    fontSize: 10,
    fontWeight: '600',
    letterSpacing: 1.2,
    marginBottom: 8,
  },
  title: {
    fontSize: 26,
    fontWeight: '800',
    letterSpacing: -0.8,
  },
  subtitle: {
    fontSize: 12,
    lineHeight: 18,
    marginTop: 7,
  },
  progressRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  progressLabel: { fontSize: 10 },
  progressTrack: { height: 5, borderRadius: 10, overflow: 'hidden', marginBottom: 18 },
  progressFill: { width: '14%', height: '100%', borderRadius: 10 },
  loading: {
    gap: 16,
  },
  cards: {
    flexDirection: 'row',
    alignItems: 'stretch',
    gap: 6,
  },
  divider: {
    alignItems: 'center',
    justifyContent: 'center',
    width: 24,
  },
  vs: {
    fontSize: 12,
    fontWeight: '600',
  },
  empty: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 48,
  },
  emptyText: {
    fontSize: 14,
  },
});
