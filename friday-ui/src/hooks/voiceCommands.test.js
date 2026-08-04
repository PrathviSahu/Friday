import { describe, it, expect } from 'vitest';
import {
  normalizeTranscript,
  matchVoiceCommand,
  shouldVerifyVoice,
} from './voiceCommands.js';

describe('normalizeTranscript', () => {
  it('lowercases and strips punctuation', () => {
    expect(normalizeTranscript('Hey Friday, open VS Code!')).toBe('open vs code');
  });

  it('strips leading and trailing wake words', () => {
    expect(normalizeTranscript('Hey Friday open trading')).toBe('open trading');
    expect(normalizeTranscript('open the career page friday')).toBe('open the career page');
    expect(normalizeTranscript('Okay friday what time is it')).toBe('what time is it');
  });

  it('strips leading polite fillers', () => {
    expect(normalizeTranscript('Please can you lock the system')).toBe('lock the system');
  });

  it('collapses whitespace and trims', () => {
    expect(normalizeTranscript('   open    trading   ')).toBe('open trading');
  });
});

describe('matchVoiceCommand — workspace & shortcuts', () => {
  it('routes trading', () => {
    expect(matchVoiceCommand('open trading mode')).toBe('trading');
    expect(matchVoiceCommand('show the charts')).toBe('trading');
  });

  it('routes career', () => {
    expect(matchVoiceCommand('open the job portal')).toBe('career');
    expect(matchVoiceCommand('show my opportunities')).toBe('career');
  });

  it('routes dashboard (NOT career)', () => {
    expect(matchVoiceCommand('open dashboard')).toBe('dashboard');
    expect(matchVoiceCommand('show the home screen')).toBe('dashboard');
  });

  it('routes lock / unlock', () => {
    expect(matchVoiceCommand('lock system')).toBe('lock');
    // 'go back to dashboard' -> 'dashboard' (frontend exits to dashboard)
    expect(matchVoiceCommand('go back to dashboard')).toBe('dashboard');
    expect(matchVoiceCommand('exit trading mode')).toBe('unlocked');
  });

  it('routes engineering / vscode / browser', () => {
    expect(matchVoiceCommand('open engineering console')).toBe('engineering');
    expect(matchVoiceCommand('open vscode')).toBe('vscode');
    expect(matchVoiceCommand('open browser')).toBe('browser');
  });

  it('routes stop / time / date / what_playing', () => {
    expect(matchVoiceCommand('stop')).toBe('stop');
    expect(matchVoiceCommand('what time is it')).toBe('time');
    expect(matchVoiceCommand("what's the date today")).toBe('date');
    expect(matchVoiceCommand('what song is playing')).toBe('what_playing');
  });
});

describe('matchVoiceCommand — open/close app objects', () => {
  it('routes workspace apps before generic open_app', () => {
    expect(matchVoiceCommand('open vs code')).toBe('vscode');
    expect(matchVoiceCommand('open chrome')).toBe('browser');
    expect(matchVoiceCommand('open engineering console')).toBe('engineering');
  });

  it('maps known apps to canonical names', () => {
    expect(matchVoiceCommand('open spotify')).toEqual({ type: 'open_app', app: 'Spotify' });
    expect(matchVoiceCommand('open brave')).toEqual({ type: 'open_app', app: 'Brave Browser' });
  });

  it('passes unknown apps through', () => {
    expect(matchVoiceCommand('open obsidian')).toEqual({ type: 'open_app', app: 'Obsidian' });
  });

  it('returns close_app objects with canonical names (even for workspace apps)', () => {
    expect(matchVoiceCommand('close spotify')).toEqual({ type: 'close_app', app: 'Spotify' });
    expect(matchVoiceCommand('close vs code')).toEqual({ type: 'close_app', app: 'Visual Studio Code' });
    expect(matchVoiceCommand('quit chrome')).toEqual({ type: 'close_app', app: 'Google Chrome' });
  });
});

describe('matchVoiceCommand — fallthrough', () => {
  it('returns null for questions (handled by the AI brain)', () => {
    expect(matchVoiceCommand('what is the meaning of life')).toBe(null);
    expect(matchVoiceCommand('how do i write a resume')).toBe(null);
  });
});

describe('shouldVerifyVoice', () => {
  it('requires >= 0.7 confidence', () => {
    expect(shouldVerifyVoice(0.72)).toBe(true);
    expect(shouldVerifyVoice(0.7)).toBe(true);
    expect(shouldVerifyVoice(0.2)).toBe(false);
    expect(shouldVerifyVoice()).toBe(false);
  });
});
