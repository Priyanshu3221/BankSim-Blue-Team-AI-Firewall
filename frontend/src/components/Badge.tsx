import React from 'react';
import { CheckCircle2, AlertTriangle, AlertOctagon, Info, ShieldCheck } from 'lucide-react';

interface RiskBadgeProps {
  score: number;
  level?: string;
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({ score, level }) => {
  let badgeClass = 'badge-safe';
  let label = level || 'LOW';
  let Icon = ShieldCheck;

  if (score > 80 || level === 'CRITICAL') {
    badgeClass = 'badge-danger';
    label = 'CRITICAL';
    Icon = AlertOctagon;
  } else if (score > 60 || level === 'HIGH') {
    badgeClass = 'badge-danger';
    label = 'HIGH';
    Icon = AlertOctagon;
  } else if (score > 25 || level === 'MEDIUM') {
    badgeClass = 'badge-warning';
    label = 'MEDIUM';
    Icon = AlertTriangle;
  }

  return (
    <span className={`badge ${badgeClass} mono`} title={`Risk Score: ${score}/100, Tier: ${label}`}>
      <Icon size={12} style={{ flexShrink: 0 }} />
      <span>{score}/100 • {label}</span>
    </span>
  );
};

interface SeverityBadgeProps {
  severity: string;
}

export const SeverityBadge: React.FC<SeverityBadgeProps> = ({ severity }) => {
  const sev = severity.toUpperCase();
  let badgeClass = 'badge-safe';
  let Icon = CheckCircle2;

  if (sev === 'CRITICAL' || sev === 'HIGH') {
    badgeClass = 'badge-danger';
    Icon = AlertOctagon;
  } else if (sev === 'MEDIUM') {
    badgeClass = 'badge-warning';
    Icon = AlertTriangle;
  } else if (sev === 'LOW') {
    badgeClass = 'badge-neutral';
    Icon = Info;
  }

  return (
    <span className={`badge ${badgeClass}`}>
      <Icon size={12} style={{ flexShrink: 0 }} />
      <span>{sev}</span>
    </span>
  );
};

interface ActionBadgeProps {
  action: string;
}

export const ActionBadge: React.FC<ActionBadgeProps> = ({ action }) => {
  const act = action.toUpperCase();
  let badgeClass = 'badge-safe';
  let Icon = CheckCircle2;

  if (act === 'BLOCK' || act === 'THREAT') {
    badgeClass = 'badge-danger';
    Icon = AlertOctagon;
  } else if (act === 'STEP_UP_VERIFICATION' || act === 'RESTRICT' || act === 'FLAG_FOR_REVIEW') {
    badgeClass = 'badge-warning';
    Icon = AlertTriangle;
  }

  return (
    <span className={`badge ${badgeClass}`}>
      <Icon size={12} style={{ flexShrink: 0 }} />
      <span>{act}</span>
    </span>
  );
};
