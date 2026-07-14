import test from 'node:test';
import assert from 'node:assert/strict';
import { normalizeTranscript, matchVoiceCommand, shouldVerifyVoice } from './voiceCommands.js';

test('normalizes and detects wake phrases', () => {
  const text = 'Hey Friday, open VS Code.';
  assert.equal(normalizeTranscript(text), 'hey friday open vs code');
  assert.equal(matchVoiceCommand(text), 'wake');
});

test('detects command phrases after wake', () => {
  assert.equal(matchVoiceCommand('open trading mode'), 'trading');
  assert.equal(matchVoiceCommand('open engineering console'), 'engineering');
  assert.equal(matchVoiceCommand('lock system'), 'lock');
});

test('requires stronger confidence for voice verification', () => {
  assert.equal(shouldVerifyVoice(0.72), true);
  assert.equal(shouldVerifyVoice(0.2), false);
});
