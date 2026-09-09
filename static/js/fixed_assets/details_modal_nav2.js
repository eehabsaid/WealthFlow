"use strict";
// Fixed asset modal — tab navigation markup, part 2 (Maintenance through
// Documents). Split out of details_modal.js (200-line backlog). Bare
// global; pure static markup, no computed values.
// ════════════════════════════════════════════════════════════════════════════

function buildFixedAssetModalTabsNavPart2() {
  return `                        <li class="nav-item d-none" role="presentation" id="maintenance-tab-item">
                          <button class="nav-link"
                              id="maintenance-tab"
                              data-bs-toggle="tab"
                              data-bs-target="#maintenance-pane"
                              type="button"
                              role="tab"
                              aria-controls="maintenance-pane"
                              aria-selected="false"
                              data-i18n="maintenance">
                            Maintenance
                          </button>
                        </li>

                        <li class="nav-item d-none" role="presentation" id="insurance-tab-item">
                          <button class="nav-link"
                              id="insurance-tab"
                              data-bs-toggle="tab"
                              data-bs-target="#insurance-pane"
                              type="button"
                              role="tab"
                              aria-controls="insurance-pane"
                              aria-selected="false"
                              data-i18n="insurance">
                            Insurance
                          </button>
                        </li>

                          <li class="nav-item" role="presentation">
                            <button class="nav-link"
                                id="furniture-tab"
                                data-bs-toggle="tab"
                                data-bs-target="#furniture-pane"
                                type="button"
                                role="tab"
                                aria-controls="furniture-pane"
                                aria-selected="false"
                                data-i18n="furniture">
                              Furniture
                            </button>
                          </li>

                          <li class="nav-item" role="presentation">
                            <button class="nav-link"
                                id="valuation-tab"
                                data-bs-toggle="tab"
                                data-bs-target="#valuation-pane"
                                type="button"
                                role="tab"
                                aria-controls="valuation-pane"
                                aria-selected="false"
                                data-i18n="valuation_history">
                              Valuation History
                            </button>
                          </li>

                          <li class="nav-item d-none" role="presentation" id="mortgage-tab-item">
                            <button class="nav-link"
                                id="mortgage-tab"
                                data-bs-toggle="tab"
                                data-bs-target="#mortgage-pane"
                                type="button"
                                role="tab"
                                aria-controls="mortgage-pane"
                                aria-selected="false"
                                data-i18n="mortgage">
                              Mortgage
                            </button>
                          </li>

                          <li class="nav-item d-none" role="presentation" id="rental-tab-item">
                            <button class="nav-link"
                                id="rental-tab"
                                data-bs-toggle="tab"
                                data-bs-target="#rental-pane"
                                type="button"
                                role="tab"
                                aria-controls="rental-pane"
                                aria-selected="false"
                                data-i18n="rental">
                              Rental
                            </button>
                          </li>

                          <li class="nav-item d-none" role="presentation" id="sale-tab-item">
                            <button class="nav-link"
                                id="sale-tab"
                                data-bs-toggle="tab"
                                data-bs-target="#sale-pane"
                                type="button"
                                role="tab"
                                aria-controls="sale-pane"
                                aria-selected="false"
                                data-i18n="sale">
                              Sale
                            </button>
                          </li>

                          <li class="nav-item" role="presentation">
                            <button class="nav-link"
                                id="documents-tab"
                                data-bs-toggle="tab"
                                data-bs-target="#documents-pane"
                                type="button"
                                role="tab"
                                aria-controls="documents-pane"
                                aria-selected="false"
                                data-i18n="documents_title">
                              Documents
                            </button>
                          </li>
              </ul>
`;
}
