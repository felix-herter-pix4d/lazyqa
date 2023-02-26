    return helpers.subprocess_output(command)
        git('add', '.', repo=repo)
        git('commit', '-m', '"added executable"', repo=repo)
    repo_dir = repo_with_executable(repo_dir)['repo'] # adds a commit to repo 'repo_dir'
    repo_with_call_inspection_executable = repo_with_executable(executable=echo_call_program)
    expected_content = ('---\n'

def test_repo_class_untracked_changes_returns_correct_patch_when_there_are_changes(repo_with_executable):
    repo_and_executable = repo_with_executable()
    with open(repo_and_executable['executable'], 'a') as file:
        file.write("untracked content")
    repo = helpers.Repo(repo_and_executable['repo'])

    patch = repo.get_untracked_changes()

    expected_content = ('--- a/app\n'
                        '+++ b/app\n'
                        '@@ -1 +1 @@\n'
                        '-echo $0 $@\n'
                        '\\ No newline at end of file\n'
                        '+echo $0 $@untracked content\n'
                        '\\ No newline at end of file')
    assert expected_content in patch


def test_repo_class_untracked_changes_returns_empty_patch_when_there_are_no_changes(repo_dir):
    repo = helpers.Repo(repo_dir)
    patch = repo.get_untracked_changes()
    assert patch == ''
