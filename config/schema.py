schema_work_package_basic = {
    "description": "Extract key elements from power plant construction projects",
    "type": "OBJECT",
    "properties": {
        "project_name": {
            "description": "Official name of the power plant project",
            "type": "STRING"
        },
        "description": {
            "description": "Project scope and objectives",
            "type": "STRING"
        },
        "plant_type": {
            "description": "Type of power generation (solar, wind, gas, coal, nuclear, etc.)",
            "type": "STRING"
        },
        "location": {
            "description": "Project location details",
            "type": "OBJECT",
            "properties": {
                "city": {
                    "description": "City where plant is located",
                    "type": "STRING"
                },
                "state": {
                    "description": "State or province",
                    "type": "STRING"
                },
                "country": {
                    "description": "Country",
                    "type": "STRING"
                }
            },
            "required": ["city", "state", "country"]
        },
        "capacity_mw": {
            "description": "Plant capacity in megawatts",
            "type": "INTEGER"
        },
        "project_timeline": {
            "description": "Key project dates",
            "type": "OBJECT",
            "properties": {
                "start_date": {
                    "description": "Project start date",
                    "type": "STRING"
                },
                "completion_date": {
                    "description": "Expected completion date",
                    "type": "STRING"
                }
            },
            "required": ["start_date", "completion_date"]
        },
        "estimated_cost_millions": {
            "description": "Total estimated cost in millions USD",
            "type": "INTEGER"
        },
        "status": {
            "description": "Current project status",
            "type": "STRING"
        }
    },
    "required": ["project_name", "description", "plant_type", "location", "capacity_mw", "project_timeline", "estimated_cost_millions", "status"]
}

schema_work_package_advanced = {
    "description": "Extract comprehensive elements from power plant construction documentation",
    "type": "OBJECT",
    "properties": {
        "project_metadata": {
            "description": "Core project identification",
            "type": "OBJECT",
            "properties": {
                "project_id": {
                    "description": "Official project identifier",
                    "type": "STRING"
                },
                "project_name": {
                    "description": "Official project name",
                    "type": "STRING"
                },
                "owner": {
                    "description": "Project owner organization",
                    "type": "STRING"
                },
                "plant_type": {
                    "description": "Power generation technology type",
                    "type": "STRING"
                },
                "capacity_mw": {
                    "description": "Plant capacity in megawatts",
                    "type": "INTEGER"
                }
            },
            "required": ["project_id", "project_name", "owner", "plant_type", "capacity_mw"]
        },
        "stakeholders": {
            "description": "Key project stakeholders and contacts",
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "role": {
                        "description": "Stakeholder role (owner, contractor, PM, etc.)",
                        "type": "STRING"
                    },
                    "organization": {
                        "description": "Organization name",
                        "type": "STRING"
                    },
                    "contact_person": {
                        "description": "Primary contact person",
                        "type": "STRING"
                    }
                },
                "required": ["role", "organization"]
            }
        },
        "technical_specs": {
            "description": "Key technical specifications",
            "type": "OBJECT",
            "properties": {
                "turbine_type": {
                    "description": "Turbine technology specification",
                    "type": "STRING"
                },
                "fuel_types": {
                    "description": "Primary and backup fuel types",
                    "type": "ARRAY",
                    "items": {
                        "type": "STRING"
                    }
                },
                "efficiency_percent": {
                    "description": "Plant efficiency percentage",
                    "type": "INTEGER"
                },
                "emission_controls": {
                    "description": "Environmental control systems",
                    "type": "ARRAY",
                    "items": {
                        "type": "STRING"
                    }
                }
            },
            "required": ["turbine_type", "fuel_types"]
        },
        "timeline_milestones": {
            "description": "Project timeline with major milestones",
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "milestone_name": {
                        "description": "Name of the milestone",
                        "type": "STRING"
                    },
                    "target_date": {
                        "description": "Target completion date",
                        "type": "STRING"
                    },
                    "status": {
                        "description": "Current milestone status",
                        "type": "STRING"
                    },
                    "description": {
                        "description": "Milestone description",
                        "type": "STRING"
                    }
                },
                "required": ["milestone_name", "target_date", "status"]
            }
        },
        "permits_approvals": {
            "description": "Required permits and regulatory approvals",
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "permit_type": {
                        "description": "Type of permit or approval",
                        "type": "STRING"
                    },
                    "issuing_authority": {
                        "description": "Government agency or authority",
                        "type": "STRING"
                    },
                    "status": {
                        "description": "Current permit status",
                        "type": "STRING"
                    },
                    "permit_number": {
                        "description": "Official permit number",
                        "type": "STRING"
                    }
                },
                "required": ["permit_type", "issuing_authority", "status"]
            }
        },
        "financial_details": {
            "description": "Project financial information",
            "type": "OBJECT",
            "properties": {
                "total_cost_millions": {
                    "description": "Total project cost in millions USD",
                    "type": "INTEGER"
                },
                "funding_sources": {
                    "description": "Sources of project funding",
                    "type": "ARRAY",
                    "items": {
                        "type": "STRING"
                    }
                },
                "ppa_buyer": {
                    "description": "Power purchase agreement buyer",
                    "type": "STRING"
                }
            },
            "required": ["total_cost_millions"]
        },
        "key_documents": {
            "description": "Important project documents and references",
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "document_type": {
                        "description": "Type of document (contract, permit, study, etc.)",
                        "type": "STRING"
                    },
                    "title": {
                        "description": "Document title",
                        "type": "STRING"
                    },
                    "document_number": {
                        "description": "Document ID or number",
                        "type": "STRING"
                    },
                    "date": {
                        "description": "Document date",
                        "type": "STRING"
                    }
                },
                "required": ["document_type", "title"]
            }
        }
    },
    "required": ["project_metadata", "stakeholders", "technical_specs", "timeline_milestones", "financial_details"]
}