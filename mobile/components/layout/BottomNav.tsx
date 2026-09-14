import React from 'react';
import { View, TouchableOpacity, Text, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../hooks/useTheme';

interface NavItem {
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  onPress: () => void;
}

interface BottomNavProps {
  items: NavItem[];
  activeIndex: number;
}

export function BottomNav({ items, activeIndex }: BottomNavProps) {
  const { colors } = useTheme();

  return (
    <View style={[styles.container, { backgroundColor: colors.tabBar, borderTopColor: colors.tabBarBorder }]}>
      {items.map((item, index) => {
        const isActive = index === activeIndex;
        return (
          <TouchableOpacity
            key={item.label}
            style={styles.item}
            onPress={item.onPress}
            activeOpacity={0.7}
          >
            <Ionicons
              name={item.icon}
              size={24}
              color={isActive ? colors.tabActive : colors.tabInactive}
            />
            <Text
              style={[
                styles.label,
                { color: isActive ? colors.tabActive : colors.tabInactive },
              ]}
            >
              {item.label}
            </Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'center',
    paddingVertical: 8,
    paddingBottom: 20,
    borderTopWidth: 1,
  },
  item: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 4,
  },
  label: {
    fontSize: 10,
    fontWeight: '500',
  },
});
