import { create } from 'zustand';

// Global state store for disaster management
export const useDisasterStore = create((set, get) => ({
  // Active disaster event data
  activeEventId: null,
  activeEventData: null,

  // Damage zones and assessment data
  damageZones: [],
  alerts: [],
  resources: [],
  deploymentRoutes: [],

  // Setter functions
  setActiveEvent: (eventId, eventData) => set({
    activeEventId: eventId,
    activeEventData: eventData
  }),

  setDamageZones: (zones) => set({ damageZones: zones }),

  setAlerts: (alerts) => set({ alerts }),

  setResources: (resources) => set({ resources }),

  addDeploymentRoute: (route) => set((state) => ({
    deploymentRoutes: [...state.deploymentRoutes, route]
  })),

  // Clear all data
  clearData: () => set({
    activeEventId: null,
    activeEventData: null,
    damageZones: [],
    alerts: [],
    resources: [],
    deploymentRoutes: []
  })
}));