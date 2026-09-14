import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { Button } from '../Button';

// Mock the useTheme hook
jest.mock('../../hooks/useTheme', () => ({
  useTheme: () => ({
    colors: {
      primary: '#10b981',
      primaryText: '#ffffff',
      text: '#f8fafc',
      textTertiary: '#64748b',
      surfaceSecondary: '#1e293b',
      border: '#334155',
    },
  }),
}));

describe('Button', () => {
  it('renders correctly', () => {
    const { getByText } = render(<Button title="Test Button" />);
    expect(getByText('Test Button')).toBeTruthy();
  });

  it('calls onPress when pressed', () => {
    const onPress = jest.fn();
    const { getByText } = render(<Button title="Test" onPress={onPress} />);
    
    fireEvent.press(getByText('Test'));
    expect(onPress).toHaveBeenCalledTimes(1);
  });

  it('does not call onPress when disabled', () => {
    const onPress = jest.fn();
    const { getByText } = render(<Button title="Test" onPress={onPress} disabled />);
    
    fireEvent.press(getByText('Test'));
    expect(onPress).not.toHaveBeenCalled();
  });

  it('shows loading indicator when isLoading', () => {
    const { queryByText } = render(<Button title="Test" isLoading />);
    expect(queryByText('Test')).toBeNull();
  });

  it('renders different variants', () => {
    const { rerender, getByText } = render(<Button title="Test" variant="primary" />);
    expect(getByText('Test')).toBeTruthy();

    rerender(<Button title="Test" variant="secondary" />);
    expect(getByText('Test')).toBeTruthy();

    rerender(<Button title="Test" variant="outline" />);
    expect(getByText('Test')).toBeTruthy();

    rerender(<Button title="Test" variant="ghost" />);
    expect(getByText('Test')).toBeTruthy();
  });

  it('renders different sizes', () => {
    const { rerender, getByText } = render(<Button title="Test" size="sm" />);
    expect(getByText('Test')).toBeTruthy();

    rerender(<Button title="Test" size="md" />);
    expect(getByText('Test')).toBeTruthy();

    rerender(<Button title="Test" size="lg" />);
    expect(getByText('Test')).toBeTruthy();
  });
});
