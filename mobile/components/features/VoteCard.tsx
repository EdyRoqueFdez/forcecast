import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useTheme } from '../../hooks/useTheme';
import { Avatar } from '../ui/Avatar';
import { Model } from '../../api/types';

interface VoteCardProps {
  model: Model;
  onPress: () => void;
  disabled?: boolean;
}

export function VoteCard({ model, onPress, disabled = false }: VoteCardProps) {
  const { colors } = useTheme();

  const getTierColor = (tier: string) => {
    switch (tier) {
      case 'elite':
        return colors.warning;
      case 'strong':
        return colors.primary;
      case 'average':
        return colors.info;
      case 'emerging':
        return colors.textSecondary;
      default:
        return colors.textSecondary;
    }
  };

  const formatPrice = (price: number) => {
    if (price === 0) return 'Free';
    return `$${price.toFixed(2)}`;
  };

  const formatContextSize = (size: number) => {
    if (size >= 1000000) {
      return `${(size / 1000000).toFixed(0)}M`;
    }
    if (size >= 1000) {
      return `${(size / 1000).toFixed(0)}K`;
    }
    return size.toString();
  };

  return (
    <TouchableOpacity
      style={[styles.container, { backgroundColor: colors.surface, borderColor: colors.border }]}
      onPress={onPress}
      disabled={disabled}
      activeOpacity={0.7}
    >
      <Avatar uri={model.avatar} name={model.name} size="lg" />
      <Text style={[styles.name, { color: colors.text }]} numberOfLines={1}>{model.name}</Text>
      <Text style={[styles.provider, { color: colors.textSecondary }]}>{model.provider}</Text>
      <View style={styles.stats}>
        <View style={styles.stat}>
          <Text style={[styles.statLabel, { color: colors.textTertiary }]}>Context</Text>
          <Text style={[styles.statValue, { color: colors.text }]}>{formatContextSize(model.context_size)}</Text>
        </View>
        <View style={styles.stat}>
          <Text style={[styles.statLabel, { color: colors.textTertiary }]}>Price</Text>
          <Text style={[styles.statValue, { color: colors.text }]}>{formatPrice(model.price_per_million)}</Text>
        </View>
        <View style={styles.stat}>
          <Text style={[styles.statLabel, { color: colors.textTertiary }]}>ELO</Text>
          <Text style={[styles.statValue, { color: getTierColor(model.tier) }]}>{model.elo_rating}</Text>
        </View>
      </View>
      <View style={[styles.eloBadge, { backgroundColor: getTierColor(model.tier) + '20' }]}>
        <Text style={[styles.eloText, { color: getTierColor(model.tier) }]}>{model.tier}</Text>
      </View>
      <View style={[styles.voteLabel, { backgroundColor: colors.primary }]}>
        <Text style={[styles.voteLabelText, { color: colors.primaryText }]}>Vote</Text>
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    borderRadius: 18,
    borderWidth: 1,
    padding: 14,
  },
  name: {
    width: '100%',
    marginTop: 10,
    fontSize: 13,
    fontWeight: '700',
    textAlign: 'center',
  },
  provider: {
    marginTop: 3,
    fontSize: 10,
  },
  stats: {
    flexDirection: 'row',
    gap: 14,
    marginTop: 12,
  },
  stat: {
    alignItems: 'center',
  },
  statLabel: {
    fontSize: 9,
  },
  statValue: {
    marginTop: 2,
    fontSize: 12,
    fontWeight: '600',
  },
  eloBadge: {
    marginTop: 11,
    paddingVertical: 4,
    paddingHorizontal: 8,
    borderRadius: 7,
  },
  eloText: { fontSize: 9, fontWeight: '700' },
  voteLabel: {
    width: '100%',
    alignItems: 'center',
    marginTop: 10,
    paddingVertical: 9,
    borderRadius: 10,
  },
  voteLabelText: { fontSize: 11, fontWeight: '800' },
});
