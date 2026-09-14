import React from 'react';
import { View, Text, Image, StyleSheet } from 'react-native';
import { useTheme } from '../../hooks/useTheme';

interface AvatarProps {
  uri?: string;
  name?: string;
  size?: 'sm' | 'md' | 'lg';
}

export function Avatar({ uri, name, size = 'md' }: AvatarProps) {
  const { colors } = useTheme();

  const getSize = () => {
    switch (size) {
      case 'sm':
        return 32;
      case 'md':
        return 48;
      case 'lg':
        return 64;
    }
  };

  const getTextSize = () => {
    switch (size) {
      case 'sm':
        return 12;
      case 'md':
        return 18;
      case 'lg':
        return 24;
    }
  };

  const getInitials = () => {
    if (!name) return '?';
    const parts = name.split(' ');
    if (parts.length >= 2) {
      return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
    }
    return name.substring(0, 2).toUpperCase();
  };

  const sizeValue = getSize();

  if (uri) {
    return (
      <Image
        source={{ uri }}
        style={[
          styles.image,
          {
            width: sizeValue,
            height: sizeValue,
            borderRadius: sizeValue / 2,
          },
        ]}
      />
    );
  }

  return (
    <View
      style={[
        styles.placeholder,
        {
          width: sizeValue,
          height: sizeValue,
          borderRadius: sizeValue / 2,
          backgroundColor: colors.primary + '30',
        },
      ]}
    >
      <Text
        style={[
          styles.initials,
          {
            color: colors.primary,
            fontSize: getTextSize(),
          },
        ]}
      >
        {getInitials()}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  image: {
    // No additional styles needed
  },
  placeholder: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  initials: {
    fontWeight: '600',
  },
});
