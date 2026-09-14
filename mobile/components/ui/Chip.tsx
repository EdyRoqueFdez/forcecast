import React from 'react';
import { TouchableOpacity, Text, StyleSheet } from 'react-native';
import { useTheme } from '../../hooks/useTheme';

interface ChipProps {
  label: string;
  selected?: boolean;
  onPress?: () => void;
  size?: 'sm' | 'md';
}

export function Chip({ label, selected = false, onPress, size = 'md' }: ChipProps) {
  const { colors } = useTheme();

  const getContainerStyle = () => {
    if (selected) {
      return {
        backgroundColor: colors.primary,
      };
    }
    return {
      backgroundColor: colors.surface,
      borderWidth: 1,
      borderColor: colors.border,
    };
  };

  const getTextStyle = () => {
    if (selected) {
      return { color: colors.primaryText };
    }
    return { color: colors.text };
  };

  const getSizeStyle = () => {
    switch (size) {
      case 'sm':
        return { paddingVertical: 4, paddingHorizontal: 8 };
      case 'md':
        return { paddingVertical: 6, paddingHorizontal: 12 };
    }
  };

  return (
    <TouchableOpacity
      style={[styles.container, getContainerStyle(), getSizeStyle()]}
      onPress={onPress}
      activeOpacity={0.7}
    >
      <Text style={[styles.text, getTextStyle()]}>{label}</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: {
    borderRadius: 9999,
    alignSelf: 'flex-start',
  },
  text: {
    fontSize: 14,
    fontWeight: '500',
  },
});
