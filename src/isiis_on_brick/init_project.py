"""Create the ISIIS Frames project on the brick Label Studio instance."""

from dotenv import find_dotenv, load_dotenv

from labelstudio_tools.projman import ProjectManager


LS_CONFIG = "configs/ls_config.isiis.json"
PROJECT_CONFIG = "configs/project_config.json"


def init_project():
    load_dotenv(find_dotenv())
    pm = ProjectManager.from_config(LS_CONFIG)
    project = pm.create_project_from_config(PROJECT_CONFIG)
    print(f"Created project: '{project.title}' (id={project.id})")
    print(f"Update ls_config.isiis.json 'project' field to {project.id} if needed.")
    return project


if __name__ == "__main__":
    init_project()
