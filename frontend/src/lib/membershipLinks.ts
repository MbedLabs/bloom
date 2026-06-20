import type { ArtefactLink, TestCampaignSummary, TestSuiteSummary } from '../api/client'

function membershipRoleForTarget(targetType: string): 'contains' | 'covers' {
  return targetType === 'TC' ? 'contains' : 'covers'
}

function suiteLink(
  suite: TestSuiteSummary,
  targetType: string,
  targetId: number,
  projectId: number,
): ArtefactLink {
  return {
    id: -10_000 - suite.id,
    project_id: projectId,
    source_type: 'TS',
    source_id: suite.id,
    target_type: targetType,
    target_id: targetId,
    role: membershipRoleForTarget(targetType),
    suspect: false,
    created_at: new Date(0).toISOString(),
  }
}

function campaignLink(
  campaign: TestCampaignSummary,
  targetType: string,
  targetId: number,
  projectId: number,
): ArtefactLink {
  return {
    id: -20_000 - campaign.id,
    project_id: projectId,
    source_type: 'CMP',
    source_id: campaign.id,
    target_type: targetType,
    target_id: targetId,
    role: membershipRoleForTarget(targetType),
    suspect: false,
    created_at: new Date(0).toISOString(),
  }
}

export function membershipLinksForSuites(
  suites: TestSuiteSummary[] | undefined,
  targetType: string,
  targetId: number,
  projectId: number,
): ArtefactLink[] {
  return (suites || []).map((suite) => suiteLink(suite, targetType, targetId, projectId))
}

export function membershipLinksForCampaigns(
  campaigns: TestCampaignSummary[] | undefined,
  targetType: string,
  targetId: number,
  projectId: number,
): ArtefactLink[] {
  return (campaigns || []).map((campaign) => campaignLink(campaign, targetType, targetId, projectId))
}
