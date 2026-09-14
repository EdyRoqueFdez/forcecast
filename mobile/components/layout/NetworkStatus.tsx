import React, { useEffect, useState } from 'react';
import { Platform, View, Text, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../hooks/useTheme';

// Safe NetInfo import for web SSR
let NetInfo: any = null;
if (Platform.OS !== 'web') {
  NetInfo = require('@react-native-community/netinfo').default;
}

interface NetworkStatusProps {
  onStatusChange?: (isConnected: boolean) => void;
}

export function NetworkStatus({ onStatusChange }: NetworkStatusProps) {
  const { colors } = useTheme();
  const [isConnected, setIsConnected] = useState(true);
  const [showBanner, setShowBanner] = useState(false);

  useEffect(() => {
    if (!NetInfo) return;

    const unsubscribe = NetInfo.addEventListener((state: any) => {
      const connected = state.isConnected ?? true;
      setIsConnected(connected);
      setShowBanner(!connected);
      onStatusChange?.(connected);
    });

    return () => unsubscribe();
  }, []);

  if (!showBanner) return null;

  return (
    <View style={[styles.banner, { backgroundColor: colors.error }]}>
      <Ionicons name="wifi-off" size={16} color={colors.white} />
      <Text style={[styles.text, { color: colors.white }]}>No internet connection</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 8,
    gap: 8,
  },
  text: {
    fontSize: 12,
    fontWeight: '500',
  },
});
