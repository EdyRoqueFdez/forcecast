import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, Alert } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../hooks/useTheme';
import { useAuth } from '../../hooks/useAuth';
import { ScreenContainer } from '../../components/layout/ScreenContainer';
import { Avatar } from '../../components/ui/Avatar';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Toggle } from '../../components/ui/Toggle';
import { Toast } from '../../components/ui/Toast';
import { i18n, Language } from '../../lib/i18n';
import { getUserVotes } from '../../api/voting';

export default function ProfileScreen() {
  const { colors, mode, toggleMode } = useTheme();
  const { user, logout, isAuthenticated } = useAuth();
  const [stats, setStats] = useState({ votes: 0, categories: 0, streak: 0 });
  const [language, setLanguage] = useState<Language>(i18n.getLanguage());
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  useEffect(() => {
    if (isAuthenticated) loadStats();
  }, [isAuthenticated]);

  const loadStats = async () => {
    try {
      const votes = await getUserVotes({ limit: 100 });
      setStats({
        votes: votes.length,
        categories: new Set(votes.map((vote) => vote.model_slug)).size,
        streak: votes.length ? 7 : 0,
      });
    } catch (error) {
      console.error('Failed to load stats:', error);
    }
  };

  const handleSignOut = () => {
    Alert.alert('Sign Out', 'Are you sure you want to sign out?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Sign Out',
        style: 'destructive',
        onPress: async () => {
          try {
            await logout();
            setToast({ message: 'Signed out successfully', type: 'success' });
          } catch (error) {
            setToast({ message: 'Failed to sign out', type: 'error' });
          }
        },
      },
    ]);
  };

  const handleLanguageToggle = async () => {
    const newLanguage: Language = language === 'en' ? 'es' : 'en';
    await i18n.setLanguage(newLanguage);
    setLanguage(newLanguage);
  };

  const recentVotes = [
    ['G4', 'GPT-4o vs Claude 3.5', 'Code · 2 min ago', 'GPT-4o'],
    ['C3', 'Claude vs Gemini 1.5', 'Writing · 15 min ago', 'Claude'],
    ['G4', 'GPT-4o vs Llama 3.1', 'Code · 3 hours ago', 'GPT-4o'],
  ];

  return (
    <ScreenContainer scrollable showBrandHeader>
      <View style={styles.header}>
        <Text style={[styles.kicker, { color: colors.primary }]}>ACCOUNT / REPUTATION</Text>
        <Avatar uri={user?.avatar} name={user?.name || 'User'} size="lg" />
        <Text style={[styles.name, { color: colors.text }]}>{user?.name || 'Forcecaster'}</Text>
        <Text style={[styles.email, { color: colors.textSecondary }]}>{user?.email || 'Member since Sep 2026'}</Text>
        <View style={styles.badges}>
          <Text style={[styles.badge, { color: colors.primary, backgroundColor: colors.primary + '20' }]}>TOP 10%</Text>
          <Text style={[styles.badge, { color: colors.warning, backgroundColor: colors.warning + '20' }]}>7-DAY STREAK</Text>
        </View>
      </View>

      <View style={styles.stats}>
        {[[stats.votes, 'Votes Cast'], [stats.categories, 'Categories'], [stats.streak, 'Day Streak']].map(([value, label]) => (
          <Card key={label} style={styles.statCard}>
            <Text style={[styles.statValue, { color: colors.primary }]}>{value}</Text>
            <Text style={[styles.statLabel, { color: colors.textSecondary }]}>{label}</Text>
          </Card>
        ))}
      </View>

      <Text style={[styles.sectionTitle, { color: colors.textSecondary }]}>Recent Votes</Text>
      <View style={styles.recentList}>
        {recentVotes.map(([avatar, vote, meta, result]) => (
          <View key={vote} style={[styles.recentItem, { backgroundColor: colors.surface, borderColor: colors.border }]}>
            <Avatar name={avatar} size="sm" />
            <View style={styles.recentInfo}>
              <Text style={[styles.recentVote, { color: colors.text }]}>{vote}</Text>
              <Text style={[styles.recentMeta, { color: colors.textTertiary }]}>{meta}</Text>
            </View>
            <Text style={[styles.recentResult, { color: colors.primary }]}>{result}</Text>
          </View>
        ))}
      </View>

      <Card style={styles.settings}>
        <View style={styles.settingRow}>
          <View style={styles.settingInfo}><Ionicons name="moon" size={18} color={colors.text} /><Text style={[styles.settingLabel, { color: colors.text }]}>Dark Mode</Text></View>
          <Toggle value={mode === 'dark'} onValueChange={toggleMode} />
        </View>
        <View style={[styles.divider, { backgroundColor: colors.border }]} />
        <View style={styles.settingRow}>
          <View style={styles.settingInfo}><Ionicons name="language" size={18} color={colors.text} /><Text style={[styles.settingLabel, { color: colors.text }]}>{language === 'en' ? 'English' : 'Español'}</Text></View>
          <Toggle value={language === 'es'} onValueChange={handleLanguageToggle} />
        </View>
      </Card>

      {isAuthenticated && <Button title="Sign Out" variant="outline" onPress={handleSignOut} leftIcon={<Ionicons name="log-out" size={18} color={colors.error} />} style={styles.signOutButton} />}
      {toast && <Toast message={toast.message} type={toast.type} onDismiss={() => setToast(null)} />}
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  header: { alignItems: 'center', paddingVertical: 8, gap: 7, marginBottom: 20 },
  kicker: { alignSelf: 'stretch', fontSize: 10, fontWeight: '600', letterSpacing: 1.2, marginBottom: 7 },
  name: { fontSize: 20, fontWeight: '800' },
  email: { fontSize: 11 },
  badges: { flexDirection: 'row', gap: 6, marginTop: 4 },
  badge: { paddingVertical: 5, paddingHorizontal: 8, borderRadius: 7, overflow: 'hidden', fontSize: 9, fontWeight: '700' },
  stats: { flexDirection: 'row', gap: 7, marginBottom: 22 },
  statCard: { flex: 1, alignItems: 'center', padding: 12 },
  statValue: { fontSize: 20, fontWeight: '800' },
  statLabel: { fontSize: 9, marginTop: 5, textTransform: 'uppercase' },
  sectionTitle: { marginBottom: 10, fontSize: 10, fontWeight: '700', letterSpacing: 1.2, textTransform: 'uppercase' },
  recentList: { gap: 7, marginBottom: 22 },
  recentItem: { flexDirection: 'row', alignItems: 'center', gap: 9, padding: 9, borderRadius: 12, borderWidth: 1 },
  recentInfo: { flex: 1 },
  recentVote: { fontSize: 10, fontWeight: '600' },
  recentMeta: { marginTop: 3, fontSize: 9 },
  recentResult: { fontSize: 9, fontWeight: '700' },
  settings: { marginBottom: 20 },
  settingRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 10 },
  settingInfo: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  settingLabel: { fontSize: 13 },
  divider: { height: 1 },
  signOutButton: { marginTop: 0 },
});
