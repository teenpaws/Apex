// Re-export the canonical axios instance and all API namespaces from the
// single source of truth so hooks can import from a consistent path.
export { apiClient } from '../api';
export {
  signalsApi,
  opportunitiesApi,
  actionsApi,
  outreachApi,
  profileApi,
  companiesApi,
  contactsApi,
  agentsApi,
  analyticsApi,
  documentsApi,
} from '../api';
export type { DocumentRecord, UploadedDoc, PendingReview } from '../api';
