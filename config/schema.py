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
            }
          },
          "required": ["name", "globalId"]
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
            }
          },
          "required": ["name", "globalId"]
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