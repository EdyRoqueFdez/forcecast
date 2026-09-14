import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, FlatList, RefreshControl } from 'react-native';
import { useTheme } from '../../hooks/useTheme';
import { ScreenContainer } from '../../components/layout/ScreenContainer';
import { Avatar } from '../../components/ui/Avatar';
import { EloBadge } from '../../components/features/EloBadge';
import { CategoryPicker } from '../../components/ui/CategoryPicker';
import { SkeletonListItem } from '../../components/ui/Skeleton';
import { Toast } from '../../components/ui/Toast';
import { Ranking } from '../../api/types';
import { getRankings } from '../../api/voting';
import { getCategories } from '../../api/meta';

export default function RankingsScreen() {
  const { colors } = useTheme();
  const [rankings, setRankings] = useState<Ranking[]>([]);
  const [selectedCategory, setSelectedCategory] = useState('coding');
  const [categories, setCategories] = useState([{ id: 'coding', name: 'Coding' }]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'error' } | null>(null);

  useEffect(() => {
    getCategories()
      .then((items) => setCategories(items.map((item) => ({ id: item.slug, name: item.name }))))
      .catch(() => undefined);
    loadRankings();
  }, [selectedCategory]);

  const loadRankings = async () => {
    setIsLoading(true);
    try {
      const response = await getRankings(selectedCategory);
      setRankings(response.rankings);
    } catch (error) {
      setToast({ message: 'Failed to load rankings', type: 'error' });
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  const onRefresh = () => {
    setIsRefreshing(true);
    loadRankings();
  };

  const renderRankingItem = ({ item, index }: { item: Ranking; index: number }) => (
    <View style={[styles.rankItem, { backgroundColor: colors.surface, borderColor: colors.border }]}>
      <View style={styles.rankNumber}>
        <Text style={[styles.rankText, { color: colors.textSecondary }]}>{index + 1}</Text>
      </View>
      <Avatar uri={item.model.avatar} name={item.model.name} size="md" />
      <View style={styles.rankInfo}>
        <Text style={[styles.modelName, { color: colors.text }]} numberOfLines={1}>
          {item.model.name}
        </Text>
        <Text style={[styles.provider, { color: colors.textSecondary }]}>{item.model.provider}</Text>
      </View>
      <EloBadge rating={item.elo_rating} delta={item.elo_delta_7d} />
    </View>
  );

  return (
    <ScreenContainer showBrandHeader>
      <View style={styles.header}>
        <Text style={[styles.kicker, { color: colors.primary }]}>SIGNAL / PUBLIC</Text>
        <Text style={[styles.title, { color: colors.text }]}>Rankings</Text>
        <Text style={[styles.subtitle, { color: colors.textSecondary }]}>Community-ranked AI models by category.</Text>
      </View>

      <CategoryPicker value={selectedCategory} options={categories} onChange={setSelectedCategory} />

      {isLoading ? (
        <View style={styles.loading}>
          {[...Array(5)].map((_, i) => (
            <SkeletonListItem key={i} />
          ))}
        </View>
      ) : rankings.length === 0 ? (
        <View style={styles.empty}>
          <Text style={[styles.emptyText, { color: colors.textSecondary }]}>
            No votes in this category yet
          </Text>
        </View>
      ) : (
        <FlatList
          data={rankings}
          renderItem={renderRankingItem}
          keyExtractor={(item) => item.model.slug}
          refreshControl={<RefreshControl refreshing={isRefreshing} onRefresh={onRefresh} />}
          contentContainerStyle={styles.list}
        />
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
  loading: {
    gap: 12,
  },
  list: {
    gap: 8,
  },
  rankItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 11,
    borderRadius: 14,
    borderWidth: 1,
    gap: 12,
  },
  rankNumber: {
    width: 24,
    alignItems: 'center',
  },
  rankText: {
    fontSize: 14,
    fontWeight: '600',
  },
  rankInfo: {
    flex: 1,
  },
  modelName: {
    fontSize: 14,
    fontWeight: '600',
  },
  provider: {
    fontSize: 12,
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
