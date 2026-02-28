import { describe, it, expect } from 'vitest';
import { todayIsoDate, RISK_LABELS, STATUS_LABELS } from '../pages/members/memberUtils';

describe('todayIsoDate', () => {
  it('returns a valid ISO date string (YYYY-MM-DD)', () => {
    const result = todayIsoDate();
    expect(result).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it('returns today date', () => {
    const today = new Date();
    const result = todayIsoDate();
    const year = today.getFullYear().toString();
    expect(result).toContain(year);
  });
});

describe('RISK_LABELS', () => {
  it('has labels for all risk levels', () => {
    expect(RISK_LABELS.green).toBe('Verde');
    expect(RISK_LABELS.yellow).toBe('Amarelo');
    expect(RISK_LABELS.red).toBe('Vermelho');
  });
});

describe('STATUS_LABELS', () => {
  it('has labels for all member statuses', () => {
    expect(STATUS_LABELS.active).toBe('Ativo');
    expect(STATUS_LABELS.paused).toBe('Pausado');
    expect(STATUS_LABELS.cancelled).toBe('Cancelado');
  });
});
