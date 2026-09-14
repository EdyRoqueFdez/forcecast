import React from 'react';
import { View, Text, ScrollView, StyleSheet, RefreshControlProps, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useTheme } from '../../hooks/useTheme';

interface ScreenContainerProps {
  children: React.ReactNode;
  safeArea?: boolean;
  scrollable?: boolean;
  padding?: boolean;
  refreshControl?: React.ReactElement;
  showBrandHeader?: boolean;
  onSearch?: () => void;
}

export function ScreenContainer({
  children,
  safeArea = true,
  scrollable = false,
  padding = true,
  refreshControl,
  showBrandHeader = false,
  onSearch,
}: ScreenContainerProps) {
  const { colors } = useTheme();

  const content = scrollable ? (
    <ScrollView
      style={[styles.scrollContent, { backgroundColor: colors.background }]}
      contentContainerStyle={[styles.scrollContainer, padding && styles.padding]}
      refreshControl={refreshControl as any}
    >
      {children}
    </ScrollView>
  ) : (
    <View style={[styles.content, padding && styles.padding]}>{children}</View>
  );

  if (safeArea) {
    return (
      <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]}>
        {showBrandHeader && <BrandHeader colors={colors} onSearch={onSearch} />}
        {content}
      </SafeAreaView>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      {showBrandHeader && <BrandHeader colors={colors} onSearch={onSearch} />}
      {content}
    </View>
  );
}

function BrandHeader({ colors, onSearch }: { colors: ReturnType<typeof useTheme>['colors']; onSearch?: () => void }) {
  return (
    <View style={[styles.brandHeader, { backgroundColor: colors.background, borderBottomColor: colors.border }]}> 
      <View style={styles.brandLockup}>
        <View style={[styles.brandMark, { backgroundColor: colors.primary }]}><Text style={{ color: colors.primaryText }}>ϟ</Text></View>
        <Text style={[styles.brandName, { color: colors.text }]}>Forcecast</Text>
      </View>
      <View style={styles.brandActions}>
        {onSearch && <TouchableOpacity onPress={onSearch} style={styles.brandAction} accessibilityLabel="Search models"><Ionicons name="search" size={19} color={colors.textTertiary} /></TouchableOpacity>}
        <TouchableOpacity style={styles.brandAction} accessibilityLabel="Notifications"><Ionicons name="notifications-outline" size={19} color={colors.textTertiary} /></TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    flex: 1,
  },
  scrollContent: {
    flex: 1,
  },
  scrollContainer: {
    flexGrow: 1,
  },
  padding: {
    paddingHorizontal: 18,
    paddingTop: 14,
    paddingBottom: 28,
  },
  brandHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    minHeight: 58,
    paddingHorizontal: 18,
    borderBottomWidth: 1,
  },
  brandLockup: { flexDirection: 'row', alignItems: 'center', gap: 9 },
  brandMark: { alignItems: 'center', justifyContent: 'center', width: 27, height: 27, borderRadius: 8 },
  brandName: { fontSize: 16, fontWeight: '800', letterSpacing: -0.5 },
  brandActions: { flexDirection: 'row', gap: 3 },
  brandAction: { alignItems: 'center', justifyContent: 'center', width: 34, height: 34, borderRadius: 10 },
});
