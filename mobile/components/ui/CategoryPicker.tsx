import React, { useState } from 'react';
import { Modal, Pressable, StyleSheet, Text, View } from 'react-native';
import { useTheme } from '../../hooks/useTheme';

interface CategoryOption {
  id: string;
  name: string;
}

interface CategoryPickerProps {
  value: string;
  options: CategoryOption[];
  onChange: (value: string) => void;
  placeholder?: string;
}

export function CategoryPicker({ value, options, onChange, placeholder = 'Select category' }: CategoryPickerProps) {
  const { colors } = useTheme();
  const [open, setOpen] = useState(false);
  const selected = options.find((option) => option.id === value);

  return (
    <>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={placeholder}
        onPress={() => setOpen(true)}
        style={[styles.trigger, { backgroundColor: colors.surface, borderColor: colors.border }]}
      >
        <View>
          <Text style={[styles.label, { color: colors.textTertiary }]}>CATEGORY</Text>
          <Text style={[styles.value, { color: colors.text }]}>{selected?.name ?? placeholder}</Text>
        </View>
        <Text style={[styles.chevron, { color: colors.primary }]}>⌄</Text>
      </Pressable>

      <Modal visible={open} transparent animationType="fade" onRequestClose={() => setOpen(false)}>
        <Pressable style={styles.backdrop} onPress={() => setOpen(false)}>
          <Pressable style={[styles.sheet, { backgroundColor: colors.surface, borderColor: colors.border }]} onPress={(event) => event.stopPropagation()}>
            <View style={[styles.handle, { backgroundColor: colors.border }]} />
            <Text style={[styles.title, { color: colors.text }]}>Choose category</Text>
            {options.map((option) => (
              <Pressable
                key={option.id}
                onPress={() => { onChange(option.id); setOpen(false); }}
                style={[styles.option, { borderBottomColor: colors.border }, option.id === value && { backgroundColor: colors.primary + '18' }]}
              >
                <Text style={[styles.optionText, { color: option.id === value ? colors.primary : colors.text }]}>{option.name}</Text>
                {option.id === value && <Text style={[styles.check, { color: colors.primary }]}>✓</Text>}
              </Pressable>
            ))}
          </Pressable>
        </Pressable>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  trigger: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', minHeight: 54, paddingHorizontal: 14, borderWidth: 1, borderRadius: 14, marginBottom: 16 },
  label: { fontSize: 9, fontWeight: '700', letterSpacing: 1 },
  value: { marginTop: 4, fontSize: 14, fontWeight: '700' },
  chevron: { fontSize: 22, lineHeight: 20 },
  backdrop: { flex: 1, justifyContent: 'flex-end', backgroundColor: 'rgba(0,0,0,0.55)' },
  sheet: { padding: 18, paddingBottom: 28, borderTopWidth: 1, borderTopLeftRadius: 24, borderTopRightRadius: 24 },
  handle: { alignSelf: 'center', width: 40, height: 4, marginBottom: 18, borderRadius: 4 },
  title: { marginBottom: 12, fontSize: 18, fontWeight: '800' },
  option: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 15, borderBottomWidth: 1 },
  optionText: { fontSize: 14, fontWeight: '600' },
  check: { fontSize: 18, fontWeight: '800' },
});
