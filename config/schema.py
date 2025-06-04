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

schema_cwp_v1 = {
  "schema_construction_work_package_piping": {
    "description": "Schema for a Construction Work Package (CWP) specifically for piping projects, detailing the minimum information extracted or defined from its Scope of Work, including a breakdown of work effort with activity-specific metadata.",
    "type": "OBJECT",
    "properties": {
      "cwp_identification": {
        "description": "Core identification details for the Construction Work Package.",
        "type": "OBJECT",
        "properties": {
          "cwp_id": {
            "description": "Unique identifier for the CWP (e.g., CWP-PIP-A01-CW-001).",
            "type": "STRING"
          },
          "project_id": {
            "description": "Identifier of the overall project this CWP belongs to (e.g., PROJ-XYZ-BLD001).",
            "type": "STRING"
          },
          "cwp_title": {
            "description": "Descriptive title for the CWP (e.g., Area 01 - Cooling Water System Piping Installation).",
            "type": "STRING"
          },
          "discipline": {
            "description": "Primary discipline covered by this CWP (e.g., Piping, Mechanical, Electrical). Should be 'Piping' for this context.",
            "type": "STRING"
          },
          "status": {
            "description": "Current status of the CWP (e.g., Planned, Released, In-Progress, Completed).",
            "type": "STRING"
          },
          "responsible_entity_ref": {
            "description": "Identifier for the contractor or internal department responsible for executing the CWP (e.g., CONTRACTOR-PIP-ALPHA).",
            "type": "STRING"
          }
        },
        "required": ["cwp_id", "project_id", "cwp_title", "discipline", "status"]
      },
      "cwp_scope": {
        "description": "Defines the scope of work, deliverables, and boundaries for the CWP.",
        "type": "OBJECT",
        "properties": {
          "scope_description": {
            "description": "A detailed narrative describing the work covered by the CWP, including what is to be installed, where, and any major exclusions.",
            "type": "STRING"
          },
          "area_designation": {
            "description": "Specifies the physical plant area or location covered by the CWP.",
            "type": "OBJECT",
            "properties": {
              "area_code": {
                "description": "Formal code for the area (e.g., AREA01).",
                "type": "STRING"
              },
              "area_name": {
                "description": "Descriptive name of the area (e.g., Process Unit A - Section 1).",
                "type": "STRING"
              },
              "grid_coordinates": {
                "description": "Grid lines or other coordinates defining the CWP boundary (e.g., A1-A5 / B1-B5).",
                "type": "STRING"
              }
            },
            "required": ["area_code", "area_name"]
          },
          "system_designation": {
            "description": "Specifies the system or sub-system the CWP pertains to.",
            "type": "OBJECT",
            "properties": {
              "system_code": {
                "description": "Code for the system (e.g., CW for Cooling Water).",
                "type": "STRING"
              },
              "system_name": {
                "description": "Full name of the system (e.g., Cooling Water System).",
                "type": "STRING"
              }
            },
            "required": ["system_code", "system_name"]
          },
          "key_deliverables_from_sow": {
            "description": "List of major outcomes or completed items expected from this CWP.",
            "type": "ARRAY",
            "items": {
              "type": "STRING"
            }
          },
          "boundary_interfaces_from_sow": {
            "description": "Details on the start/end points and interfaces with other work packages or disciplines.",
            "type": "OBJECT",
            "properties": {
              "start_points_tie_ins": {
                "description": "List of incoming tie-in points or interfaces.",
                "type": "ARRAY",
                "items": {
                  "type": "OBJECT",
                  "properties": {
                    "tie_in_id": {"type": "STRING", "description": "Identifier for the tie-in point."},
                    "description": {"type": "STRING", "description": "Description of the tie-in or interface."}
                  },
                  "required": ["tie_in_id"]
                }
              },
              "end_points_tie_ins": {
                "description": "List of outgoing tie-in points or interfaces.",
                "type": "ARRAY",
                "items": {
                  "type": "OBJECT",
                  "properties": {
                    "tie_in_id": {"type": "STRING", "description": "Identifier for the tie-in point."},
                    "description": {"type": "STRING", "description": "Description of the tie-in or interface."}
                  },
                  "required": ["tie_in_id"]
                }
              },
              "exclusions_from_sow": {
                "description": "Specific items or tasks explicitly excluded from this CWP's scope.",
                "type": "ARRAY",
                "items": {
                  "type": "STRING"
                }
              }
            },
            "required": []
          }
        },
        "required": ["scope_description", "area_designation", "system_designation", "key_deliverables_from_sow"]
      },
      "cwp_technical_details": {
        "description": "Technical specifications, drawings, and estimated quantities relevant to the CWP.",
        "type": "OBJECT",
        "properties": {
          "principal_material_specifications_summary": {
            "description": "High-level summary of key material specifications (e.g., Piping Class, Material Grade, Governing Code).",
            "type": "ARRAY",
            "items": {
              "type": "STRING"
            }
          },
          "governing_engineering_documents_ref": {
            "description": "References to key engineering documents that define or support the CWP scope.",
            "type": "OBJECT",
            "properties": {
              "p_and_id_list": {
                "description": "List of relevant Piping and Instrumentation Diagram numbers.",
                "type": "ARRAY",
                "items": {"type": "STRING"}
              },
              "general_arrangement_drawing_list": {
                "description": "List of relevant General Arrangement drawing numbers.",
                "type": "ARRAY",
                "items": {"type": "STRING"}
              },
              "line_list_reference": {
                "description": "Reference to the applicable Line List document/version.",
                "type": "STRING"
              }
            },
            "required": []
          },
          "estimated_quantities_summary": {
            "description": "High-level summary of major commodity quantities derived from the SOW.",
            "type": "OBJECT",
            "properties": {
              "pipe_linear_meters_approx": {
                "description": "Approximate linear meters of pipe.",
                "type": "INTEGER"
              },
              "number_of_spools_approx": {
                "description": "Approximate number of pipe spools.",
                "type": "INTEGER"
              },
              "number_of_valves_approx": {
                "description": "Approximate number of valves.",
                "type": "INTEGER"
              }
            },
            "required": []
          }
        },
        "required": []
      },
      "cwp_work_effort_breakdown": {
        "description": "Breakdown of distinct construction or installation activities derived from the CWP scope, with optional level of effort and metadata.",
        "type": "OBJECT",
        "properties": {
          "activities": {
            "description": "List of distinct activities involved in the CWP.",
            "type": "ARRAY",
            "items": {
              "type": "OBJECT",
              "properties": {
                "activity_description": {
                  "description": "Description of the specific construction or installation activity.",
                  "type": "STRING"
                },
                "estimated_hours": {
                  "description": "Estimated level of effort for the activity in hours. Include if a value is provided or is obvious, otherwise use 0.0 and may be populated later.",
                  "type": "INTEGER"
                },
                "metadata": {
                  "description": "Optional additional metadata for the activity.",
                  "type": "OBJECT",
                  "properties": {
                    "activity_id": {
                      "description": "A unique identifier for this specific activity, if applicable.",
                      "type": "STRING"
                    },
                    "activity_name": {
                      "description": "A short name or title for the activity, if different from the description.",
                      "type": "STRING"
                    },
                    "specification_references": {
                      "description": "References to relevant specifications, drawings, or standards for this activity.",
                      "type": "ARRAY",
                      "items": {
                        "type": "STRING"
                      }
                    },
                    "material_ids": {
                      "description": "List of material IDs or codes primarily associated with this activity.",
                      "type": "ARRAY",
                      "items": {
                        "type": "STRING"
                      }
                    },
                    "equipment_ids_required": {
                      "description": "List of specific equipment IDs or types required for this activity.",
                      "type": "ARRAY",
                      "items": {
                        "type": "STRING"
                      }
                    }
                  },
                  "required": []
                }
              },
              "required": ["activity_description", "estimated_hours", "metadata"]
            }
          }
        },
        "required": ["activities"]
      },
      "cwp_schedule": {
        "description": "Planned schedule information for the CWP.",
        "type": "OBJECT",
        "properties": {
          "planned_start_date_cwp": {
            "description": "The planned start date for the CWP (YYYY-MM-DD).",
            "type": "STRING",
            "format": "date"
          },
          "planned_finish_date_cwp": {
            "description": "The planned finish date for the CWP (YYYY-MM-DD).",
            "type": "STRING",
            "format": "date"
          }
        },
        "required": ["planned_start_date_cwp", "planned_finish_date_cwp"]
      }
    },
    "required": [
      "cwp_identification",
      "cwp_scope",
      "cwp_technical_details",
      "cwp_work_effort_breakdown",
      "cwp_schedule"
    ]
  }
}

schema_task_based_work_package = {
    "description": "Extract task-based work package information from Statement of Work documents, focusing on individual tasks with dependencies and resource requirements",
    "type": "OBJECT",
    "properties": {
        "project_metadata": {
            "description": "Basic project identification information",
            "type": "OBJECT",
            "properties": {
                "project_id": {
                    "description": "Unique project identifier",
                    "type": "STRING"
                },
                "project_name": {
                    "description": "Project name or title",
                    "type": "STRING"
                },
                "document_title": {
                    "description": "Title of the source document",
                    "type": "STRING"
                },
                "document_date": {
                    "description": "Date of the document",
                    "type": "STRING"
                },
                "work_package_id": {
                    "description": "Unique identifier for this work package",
                    "type": "STRING"
                },
                "work_package_description": {
                    "description": "Brief description of the overall work package scope",
                    "type": "STRING"
                }
            },
            "required": ["project_name", "work_package_description"]
        },
        "tasks": {
            "description": "List of individual tasks extracted from the Statement of Work",
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "task_id": {
                        "description": "Unique identifier for the task (e.g., TASK-001, T001, etc.). Must be unique within the work package.",
                        "type": "STRING"
                    },
                    "task_description": {
                        "description": "Detailed description of what the task entails",
                        "type": "STRING"
                    },
                    "duration_days": {
                        "description": "Calendar duration in days required to complete the task.  If not available, use 0.",
                        "type": "INTEGER"
                    },
                    "level_of_effort_hours": {
                        "description": "Total man-hours required to complete the task.  If not available, use 0.",
                        "type": "NUMBER"
                    },
                    "dependencies": {
                        "description": "Task dependencies and execution requirements",
                        "type": "OBJECT",
                        "properties": {
                            "prerequisite_tasks": {
                                "description": "List of task IDs that must be completed before this task can start",
                                "type": "ARRAY",
                                "items": {
                                    "type": "STRING"
                                }
                            },
                            "execution_type": {
                                "description": "Whether this task can be executed in parallel with other tasks or must be done in series",
                                "type": "STRING",
                                "enum": ["parallel", "series"]
                            },
                            "specialist_required": {
                                "description": "Type of specialist required to complete this task",
                                "type": "STRING",
                                "enum": ["pipefitter", "welder", "inspector"]
                            }
                        },
                        "required": ["prerequisite_tasks", "execution_type", "specialist_required"]
                    },
                    "z_location_meters": {
                        "description": "Height or z-coordinate location in meters where the task result will be positioned after completion (optional)",
                        "type": "NUMBER"
                    }
                },
                "required": ["task_id", "task_description", "duration_days", "level_of_effort_hours", "dependencies"]
            }
        }
    },
    "required": ["project_metadata", "tasks"]
}

ifc_schema = {
  "description": "Summarizes key components and metadata of 3D CAD data from an IFC string.",
  "type": "OBJECT",
  "properties": {
    "projectMetadata": {
      "description": "Overall project identification and authorship information.",
      "type": "OBJECT",
      "properties": {
        "projectName": {
          "description": "Name of the overall project.",
          "type": "STRING"
        },
        "globalId": {
          "description": "Globally unique identifier for the project.",
          "type": "STRING"
        },
        "schemaVersion": {
          "description": "IFC schema version used (e.g., IFC4).",
          "type": "STRING"
        },
        "creationDate": {
          "description": "Date and time when the IFC file was created.",
          "type": "STRING",
          "format": "date-time"
        },
        "authoringTool": {
          "description": "Software used to author the IFC model.",
          "type": "STRING"
        },
        "organization": {
          "description": "Organization that authored the IFC model.",
          "type": "STRING"
        },
        "description": {
          "description": "General description of the project.",
          "type": "STRING"
        }
      },
      "required": ["projectName", "globalId", "schemaVersion"]
    },
    "overallSpatialPlacement": {
      "description": "High-level positioning and orientation of the model's site and main building.",
      "type": "OBJECT",
      "properties": {
        "site": {
          "description": "Geographical placement information for the site.",
          "type": "OBJECT",
          "properties": {
            "name": {
              "description": "Name of the site.",
              "type": "STRING"
            },
            "globalId": {
              "description": "Globally unique identifier for the site.",
              "type": "STRING"
            },
            "easting": {
              "description": "Easting coordinate of the site's origin.",
              "type": "NUMBER"
            },
            "northing": {
              "description": "Northing coordinate of the site's origin.",
              "type": "NUMBER"
            },
            "elevation": {
              "description": "Elevation of the site's origin.",
              "type": "NUMBER"
            },
            "trueNorthOrientation": {
              "description": "Angle in degrees from the Y-axis to true North.",
              "type": "NUMBER"
            }
          },
          "required": ["globalId"]
        },
        "building": {
          "description": "Main building's placement relative to the site.",
          "type": "OBJECT",
          "properties": {
            "name": {
              "description": "Name of the building.",
              "type": "STRING"
            },
            "globalId": {
              "description": "Globally unique identifier for the building.",
              "type": "STRING"
            },
            "x": {
              "description": "X-coordinate of the building's origin.",
              "type": "NUMBER"
            },
            "y": {
              "description": "Y-coordinate of the building's origin.",
              "type": "NUMBER"
            },
            "z": {
              "description": "Z-coordinate (elevation) of the building's origin.",
              "type": "NUMBER"
            },
            "rotationDegrees": {
              "description": "Rotation of the building in degrees around X, Y, and Z axes.",
              "type": "OBJECT",
              "properties": {
                "x": {
                  "type": "NUMBER"
                },
                "y": {
                  "type": "NUMBER"
                },
                "z": {
                  "type": "NUMBER"
                }
              }
            }
          },
          "required": ["globalId", "x", "y", "z"]
        }
      },
      "required": ["site", "building"]
    },
    "componentSummary": {
      "description": "Statistical overview and bounding volume of all components.",
      "type": "OBJECT",
      "properties": {
        "totalComponents": {
          "description": "Total number of individual components in the design.",
          "type": "INTEGER"
        },
        "componentTypes": {
          "description": "Breakdown of components by type with counts and an example GlobalId.",
          "type": "ARRAY",
          "items": {
            "type": "OBJECT",
            "properties": {
              "type": {
                "description": "IFC type of the component (e.g., IfcWall, IfcDoor).",
                "type": "STRING"
              },
              "count": {
                "description": "Number of components of this type.",
                "type": "INTEGER"
              },
              "exampleGlobalId": {
                "description": "An example GlobalId for a component of this type.",
                "type": "STRING"
              }
            },
            "required": ["type", "count"]
          }
        },
        "boundingVolume": {
          "description": "Overall bounding box encompassing all model components.",
          "type": "OBJECT",
          "properties": {
            "minX": {
              "type": "NUMBER"
            },
            "minY": {
              "type": "NUMBER"
            },
            "minZ": {
              "type": "NUMBER"
            },
            "maxX": {
              "type": "NUMBER"
            },
            "maxY": {
              "type": "NUMBER"
            },
            "maxZ": {
              "type": "NUMBER"
            }
          },
          "required": ["minX", "minY", "minZ", "maxX", "maxY", "maxZ"]
        }
      },
      "required": ["totalComponents", "componentTypes", "boundingVolume"]
    },
    "components": {
      "description": "A list of individual 3D CAD components with their key properties.",
      "type": "ARRAY",
      "items": {
        "type": "OBJECT",
        "properties": {
          "globalId": {
            "description": "Globally unique identifier for the component.",
            "type": "STRING"
          },
          "name": {
            "description": "Name or common identifier of the component.",
            "type": "STRING"
          },
          "type": {
            "description": "IFC type of the component (e.g., IfcWall, IfcDoor).",
            "type": "STRING"
          },
          "storey": {
            "description": "The building storey/level to which the component belongs.",
            "type": "STRING"
          },
          "material": {
            "description": "Primary material assigned to the component.",
            "type": "STRING"
          },
          "x": {
            "description": "X-coordinate of the component's origin.",
            "type": "NUMBER"
          },
          "y": {
            "description": "Y-coordinate of the component's origin.",
            "type": "NUMBER"
          },
          "z": {
            "description": "Z-coordinate (elevation) of the component's origin.",
            "type": "NUMBER"
          },
          "rotationDegrees": {
            "description": "Rotation of the component in degrees around X, Y, and Z axes.",
            "type": "OBJECT",
            "properties": {
              "x": {
                "type": "NUMBER"
              },
              "y": {
                "type": "NUMBER"
              },
              "z": {
                "type": "NUMBER"
              }
            }
          },
          "dimensions": {
            "description": "Approximate overall dimensions of the component.",
            "type": "OBJECT",
            "properties": {
              "length": {
                "type": "NUMBER"
              },
              "width": {
                "type": "NUMBER"
              },
              "height": {
                "type": "NUMBER"
              }
            }
          }
        },
        "required": ["globalId", "name", "type", "x", "y", "z"]
      }
    }
  },
  "required": ["projectMetadata", "overallSpatialPlacement", "componentSummary", "components"]
}