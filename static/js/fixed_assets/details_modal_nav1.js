"use strict";
// Fixed asset modal — tab navigation markup, part 1 (General through
// Renovations). Split out of details_modal.js (200-line backlog). Bare
// global; pure static markup, no computed values.
// ════════════════════════════════════════════════════════════════════════════

function buildFixedAssetModalTabsNavPart1() {
  return `              <ul class="nav nav-tabs mb-4" id="fixedAssetTabs" role="tablist">
                  <li class="nav-item" role="presentation">
                      <button class="nav-link active"
                              id="general-tab"
                              data-bs-toggle="tab"
                              data-bs-target="#general-pane"
                              type="button"
                              role="tab"
                              aria-controls="general-pane"
                              aria-selected="true"
                              data-i18n="general">
                          General
                      </button>
                  </li>

                  <li class="nav-item" role="presentation">
                      <button class="nav-link"
                              id="property-tab"
                              data-bs-toggle="tab"
                              data-bs-target="#property-pane"
                              type="button"
                              role="tab"
                              aria-controls="property-pane"
                              aria-selected="false"
                              data-i18n="property">
                          Property
                      </button>
                  </li>

                    <li class="nav-item d-none" role="presentation" id="vehicle-tab-item">
                      <button class="nav-link"
                          id="vehicle-tab"
                          data-bs-toggle="tab"
                          data-bs-target="#vehicle-pane"
                          type="button"
                          role="tab"
                          aria-controls="vehicle-pane"
                          aria-selected="false"
                          data-i18n="vehicle">
                        Vehicle
                      </button>
                    </li>

                    <li class="nav-item d-none" role="presentation" id="gold-tab-item">
                      <button class="nav-link"
                          id="gold-tab"
                          data-bs-toggle="tab"
                          data-bs-target="#gold-pane"
                          type="button"
                          role="tab"
                          aria-controls="gold-pane"
                          aria-selected="false"
                          data-i18n="gold_details">
                        Gold Details
                      </button>
                    </li>

                    <li class="nav-item d-none" role="presentation" id="other-details-tab-item">
                      <button class="nav-link"
                          id="other-details-tab"
                          data-bs-toggle="tab"
                          data-bs-target="#other-details-pane"
                          type="button"
                          role="tab"
                          aria-controls="other-details-pane"
                          aria-selected="false"
                          data-i18n="details">
                        Details
                      </button>
                    </li>

                    <li class="nav-item" role="presentation">
                      <button class="nav-link"
                          id="photos-tab"
                          data-bs-toggle="tab"
                          data-bs-target="#photos-pane"
                          type="button"
                          role="tab"
                          aria-controls="photos-pane"
                          aria-selected="false"
                          data-i18n="photos">
                        Photos
                      </button>
                    </li>

                  <li class="nav-item" role="presentation">
                      <button class="nav-link"
                              id="renovation-tab"
                              data-bs-toggle="tab"
                              data-bs-target="#renovation-pane"
                              type="button"
                              role="tab"
                              aria-controls="renovation-pane"
                              aria-selected="false"
                              data-i18n="renovations">
                          Renovations
                      </button>
                  </li>
`;
}
