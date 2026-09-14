import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTheme } from '../../hooks/useTheme';

interface EloBadgeProps {
  rating: number;
  delta?: number;
  size?: 'sm' | 'md' | 'lg';
}

export function EloBadge({ rating, delta, size = 'md' }: EloBadgeProps) {
  const { colors } = useTheme();

  const getTier = (rating: number) => {
    if (rating >= 1500) return { label: 'Elite', color: colors.warning };
    if (rating >= 1300) return { label: 'Strong', color: colors.primary };
    if (rating >= 1100) return { label: 'Average', color: colors.info };
    return { label: 'Emerging', color: colors.textSecondary };
  };

  const tier = getTier(rating);

  const getSizeStyle = () => {
    switch (size) {
      case 'sm':
        return { paddingVertical: 2, paddingHorizontal: 6 };
      case 'md':
        return { paddingVertical: 4, paddingHorizontal: 8 };
      case 'lg':
        return { paddingVertical: 6, paddingHorizontal: 12 };
    }
  };

  const getTextSizeStyle = () => {
    switch (size) {
      case 'sm':
        return { fontSize: 10 };
      case 'md':
        return { fontSize: 12 };
      case 'lg':
        return { fontSize: 14 };
    }
  };

  return (
    <View style={[styles.container, getSizeStyle(), { backgroundColor: tier.color + '20' }]}>
      <Text style={[styles.rating, { color: tier.color }, getTextSizeStyle()]}>{rating}</Text>
      {delta !== undefined && (
        <Text
          style={[
            styles.delta,
            { color: delta >= 0 ? colors.success : colors.error },
            getTextSizeStyle(),
          ]}
        >
          {delta >= 0 ? `+${delta}` : delta}
        </Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: 9999,
    gap: 4,
  },
  rating: {
    fontWeight: '600',
  },
  delta: {
    fontWeight: '500',
  },
});
