import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, FlatList, RefreshControl, TextInput, ScrollView } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../hooks/useTheme';
import { ScreenContainer } from '../../components/layout/ScreenContainer';
import { Avatar } from '../../components/ui/Avatar';
import { Badge } from '../../components/ui/Badge';
import { Chip } from '../../components/ui/Chip';
import { SkeletonListItem } from '../../components/ui/Skeleton';
import { Toast } from '../../components/ui/Toast';
import { Model } from '../../api/types';
import { getModels } from '../../api/models';

const PROVIDERS = ['All', 'OpenAI', 'Anthropic', 'Google', 'Meta', 'Mistral'];

export default function ModelsScreen() {
  const { colors } = useTheme();
  const [models, setModels] = useState<Model[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedProvider, setSelectedProvider] = useState('All');
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'error' } | null>(null);

  useEffect(() => {
    loadModels();
  }, [selectedProvider]);

  const loadModels = async () => {
    setIsLoading(true);
    try {
      const response = await getModels({
        provider: selectedProvider === 'All' ? undefined : selectedProvider,
        search: searchQuery || undefined,
      });
      setModels(response.models);
    } catch (error) {
      setToast({ message: 'Failed to load models', type: 'error' });
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  const handleSearch = () => {
    loadModels();
  };

  const onRefresh = () => {
    setIsRefreshing(true);
    loadModels();
  };

  const renderModelItem = ({ item }: { item: Model }) => (
    <View style={[styles.modelItem, { backgroundColor: colors.surface, borderColor: colors.border }]}>
      <Avatar uri={item.avatar} name={item.name} size="md" />
      <View style={styles.modelInfo}>
        <Text style={[styles.modelName, { color: colors.text }]} numberOfLines={1}>
          {item.name}
        </Text>
        <Text style={[styles.provider, { color: colors.textSecondary }]}>{item.provider}</Text>
        <View style={styles.tags}>
          {item.categories.slice(0, 2).map((cat) => (
            <Badge key={cat} label={cat} size="sm" />
          ))}
        </View>
      </View>
      <View style={styles.eloContainer}>
        <Text style={[styles.elo, { color: colors.primary }]}>{item.elo_rating}</Text>
        <Text style={[styles.tier, { color: colors.textTertiary }]}>{item.tier}</Text>
      </View>
    </View>
  );

  return (
    <ScreenContainer showBrandHeader>
      <View style={styles.header}>
        <Text style={[styles.kicker, { color: colors.primary }]}>CATALOG / APPROVED</Text>
        <Text style={[styles.title, { color: colors.text }]}>Models</Text>
        <Text style={[styles.subtitle, { color: colors.textSecondary }]}>Browse approved models and compare their signal.</Text>
      </View>

      <View style={[styles.searchContainer, { backgroundColor: colors.surface, borderColor: colors.border }]}>
        <Ionicons name="search" size={20} color={colors.textTertiary} />
        <TextInput
          style={[styles.searchInput, { color: colors.text }]}
          placeholder="Search models..."
          placeholderTextColor={colors.textTertiary}
          value={searchQuery}
          onChangeText={setSearchQuery}
          onSubmitEditing={handleSearch}
          returnKeyType="search"
        />
      </View>

      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.providers}>
        {PROVIDERS.map((provider) => (
          <Chip
            key={provider}
            label={provider}
            selected={selectedProvider === provider}
            onPress={() => setSelectedProvider(provider)}
            size="sm"
          />
        ))}
      </ScrollView>

      {isLoading ? (
        <View style={styles.loading}>
          {[...Array(8)].map((_, i) => (
            <SkeletonListItem key={i} />
          ))}
        </View>
      ) : models.length === 0 ? (
        <View style={styles.empty}>
          <Text style={[styles.emptyText, { color: colors.textSecondary }]}>
            No models match your search
          </Text>
        </View>
      ) : (
        <FlatList
          data={models}
          renderItem={renderModelItem}
          keyExtractor={(item) => item.slug}
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
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    borderWidth: 1,
    borderRadius: 12,
    marginBottom: 12,
  },
  searchInput: {
    flex: 1,
    paddingVertical: 12,
    paddingHorizontal: 8,
    fontSize: 16,
  },
  providers: {
    marginBottom: 16,
  },
  loading: {
    gap: 12,
  },
  list: {
    gap: 8,
  },
  modelItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    borderRadius: 12,
    borderWidth: 1,
    gap: 12,
  },
  modelInfo: {
    flex: 1,
  },
  modelName: {
    fontSize: 14,
    fontWeight: '600',
  },
  provider: {
    fontSize: 12,
    marginTop: 2,
  },
  tags: {
    flexDirection: 'row',
    gap: 4,
    marginTop: 6,
  },
  eloContainer: {
    alignItems: 'center',
  },
  elo: {
    fontSize: 16,
    fontWeight: '700',
  },
  tier: {
    fontSize: 10,
    marginTop: 2,
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
