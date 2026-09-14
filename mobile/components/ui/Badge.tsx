import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTheme } from '../../hooks/useTheme';

interface BadgeProps {
  label: string;
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info';
  size?: 'sm' | 'md';
}

export function Badge({ label, variant = 'default', size = 'md' }: BadgeProps) {
  const { colors } = useTheme();

  const getBackgroundColor = () => {
    switch (variant) {
      case 'success':
        return colors.success + '20';
      case 'warning':
        return colors.warning + '20';
      case 'error':
        return colors.error + '20';
      case 'info':
        return colors.info + '20';
      default:
        return colors.surfaceSecondary;
    }
  };

  const getTextColor = () => {
    switch (variant) {
      case 'success':
        return colors.success;
      case 'warning':
        return colors.warning;
      case 'error':
        return colors.error;
      case 'info':
        return colors.info;
      default:
        return colors.textSecondary;
    }
  };

  const getSizeStyle = () => {
    switch (size) {
      case 'sm':
        return { paddingVertical: 2, paddingHorizontal: 6 };
      case 'md':
        return { paddingVertical: 4, paddingHorizontal: 8 };
    }
  };

  const getTextSizeStyle = () => {
    switch (size) {
      case 'sm':
        return { fontSize: 10 };
      case 'md':
        return { fontSize: 12 };
    }
  };

  return (
    <View style={[styles.container, { backgroundColor: getBackgroundColor() }, getSizeStyle()]}>
      <Text style={[styles.text, { color: getTextColor() }, getTextSizeStyle()]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    borderRadius: 9999,
    alignSelf: 'flex-start',
  },
  text: {
    fontWeight: '600',
  },
});
