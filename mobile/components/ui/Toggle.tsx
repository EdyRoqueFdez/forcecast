import React from 'react';
import { TouchableOpacity, StyleSheet, Animated } from 'react-native';
import { useTheme } from '../../hooks/useTheme';

interface ToggleProps {
  value: boolean;
  onValueChange: (value: boolean) => void;
  disabled?: boolean;
  size?: 'sm' | 'md';
}

export function Toggle({ value, onValueChange, disabled = false, size = 'md' }: ToggleProps) {
  const { colors } = useTheme();

  const getSize = () => {
    switch (size) {
      case 'sm':
        return { width: 44, height: 24, thumb: 20 };
      case 'md':
        return { width: 52, height: 28, thumb: 24 };
    }
  };

  const sizeConfig = getSize();

  const getBackgroundColor = () => {
    if (disabled) return colors.surfaceSecondary;
    return value ? colors.primary : colors.surfaceSecondary;
  };

  const getThumbColor = () => {
    if (disabled) return colors.textTertiary;
    return value ? colors.primaryText : colors.text;
  };

  return (
    <TouchableOpacity
      style={[
        styles.container,
        {
          width: sizeConfig.width,
          height: sizeConfig.height,
          backgroundColor: getBackgroundColor(),
          borderRadius: sizeConfig.height / 2,
          justifyContent: value ? 'flex-end' : 'flex-start',
          paddingHorizontal: 2,
        },
        disabled && styles.disabled,
      ]}
      onPress={() => !disabled && onValueChange(!value)}
      activeOpacity={0.8}
    >
      <Animated.View
        style={[
          styles.thumb,
          {
            width: sizeConfig.thumb,
            height: sizeConfig.thumb,
            borderRadius: sizeConfig.thumb / 2,
            backgroundColor: getThumbColor(),
          },
        ]}
      />
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: {
    // Base styles applied dynamically
  },
  thumb: {
    // Thumb styles applied dynamically
  },
  disabled: {
    opacity: 0.5,
  },
});
