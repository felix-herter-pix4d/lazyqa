# lazyqa

This folder contains a collection of scripts aiming at simplifying the life
of developers when doing QA during the work on
[fastmap repo](https://github.com/Pix4D/pix4d-rag).

## Content

**Modules to simplify bookkeeping** of `test_pipeline` and `test_ortho`
invocations.
* `lazytp.py` is a wrapper of `test_pipeline`
* `lazyto.py` is a wrapper of `test_ortho`

**Modules that enable batch processing**, that is, calling `test_pipeline` and `test_ortho` for
a set of datasets.
* `batchltp.py`
* `batchlto.py` to be done

These modules can be executed and automatically create enumerated
output folders into which the the execution artifacts are stored. They take
care of other functionality that might come in handy, such as

* automatic re-compilation before calling the `test_...` executables,
* warning the user when calling stale executables,
* storing of the repo state at the time of execution in patch files inside the
  output folder (handy for looking up what code changes were performed to
  create the results),
* allowing the user to add a description to the result names, describing the
  nature of the changes that are tested,
* automatic renaming of the orthos,
* storing of the logs,
* storing of the `.ini` files used to configure the executables,
* simplify running `test_ortho` from outputs produced using `test_pipeline`.

## Usage

For dependency management `pipenv` is used, but the code should run with bare
`python 3.10`.

To install `pipenv`, do
```
pip install pipenv
```

Activating a shell with all requirements installed, execute inside the `lazyqa` folder
```
pipenv shell
```

### Running the Tests

To install the development packages (see `Pipfile`), execute inside the `lazyqa` folder
```
pipenv install --dev
```

To execute the tests, execute inside the `lazyqa` folder, in a shell with dev-dependencies.
```
pytest
```


## Code Layout

Each module `mymodule.py` has a corresponding module `test_mymodle.py` containing tests.

Functionality that is relevant to more then just one module is in `common.py`.