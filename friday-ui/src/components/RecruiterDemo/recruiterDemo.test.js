import { describe, it, expect } from 'vitest';
import {
  DEMO_CAPABILITIES,
  DEMO_JOBS,
  DEMO_EMAIL_THREAD,
  DEMO_CALENDAR_EVENT,
  DEMO_TOUR_STEPS,
  DEMO_ARCHITECTURE_LAYERS
} from './demoData.js';

describe('Phase 6.9 Recruiter Demo Dataset & Tour Integrity', () => {
  it('defines all 7 core capability subsystems', () => {
    expect(DEMO_CAPABILITIES).toHaveLength(7);
    const ids = DEMO_CAPABILITIES.map(c => c.id);
    expect(ids).toContain('voice');
    expect(ids).toContain('career');
    expect(ids).toContain('email');
    expect(ids).toContain('calendar');
    expect(ids).toContain('trading');
    expect(ids).toContain('memory');
    expect(ids).toContain('security');
  });

  it('provides 8 sequential recruiter tour steps with prompt and response', () => {
    expect(DEMO_TOUR_STEPS).toHaveLength(8);
    DEMO_TOUR_STEPS.forEach((step, idx) => {
      expect(step.step).toBe(idx + 1);
      expect(step.title).toBeTruthy();
      expect(step.prompt).toBeTruthy();
      expect(step.response).toBeTruthy();
    });
  });

  it('contains realistic Java job postings with match scores and ATS data', () => {
    expect(DEMO_JOBS.length).toBeGreaterThanOrEqual(3);
    const topJob = DEMO_JOBS[0];
    expect(topJob.title).toContain('Java');
    expect(topJob.matchScore).toBeGreaterThanOrEqual(90);
    expect(topJob.skills).toContain('Spring Boot 3');
    expect(topJob.salary).toContain('₹');
    expect(topJob.atsScore).toBeGreaterThan(80);
  });

  it('provides email draft with cryptographic security digest and approval boundary', () => {
    expect(DEMO_EMAIL_THREAD.draftResponse.status).toContain('APPROVAL_REQUIRED');
    expect(DEMO_EMAIL_THREAD.draftResponse.securityHash).toHaveLength(64); // sha-256
    expect(DEMO_EMAIL_THREAD.draftResponse.body).toContain('Thursday at 3:00 PM IST');
  });

  it('provides calendar event with collision-free verification', () => {
    expect(DEMO_CALENDAR_EVENT.collisionCheck).toContain('0 Collisions Detected');
    expect(DEMO_CALENDAR_EVENT.status).toContain('APPROVAL_REQUIRED');
  });

  it('covers all 6 architectural pipeline layers without exposing secrets', () => {
    expect(DEMO_ARCHITECTURE_LAYERS).toHaveLength(6);
    const layers = DEMO_ARCHITECTURE_LAYERS.map(l => l.layer);
    expect(layers).toContain('VOICE_STT');
    expect(layers).toContain('INTENT_BRAIN');
    expect(layers).toContain('CONTEXT_MEMORY');
    expect(layers).toContain('TOOL_EXECUTION');
    expect(layers).toContain('SECURITY_GATE');
    expect(layers).toContain('AUDIT_PERSIST');

    // Verify zero hardcoded tokens or private filepaths
    const allText = JSON.stringify(DEMO_ARCHITECTURE_LAYERS);
    expect(allText).not.toContain('prod_super_secret');
    expect(allText).not.toContain('/Users/');
  });
});
