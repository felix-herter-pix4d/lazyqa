# Script to rapidly assess the effect that a code change has to a wide variety
# of datasets.
#
# It enables to compare the results of applying a test version of the binary
# to a set of QA datasets against the results produced by a reference version.
#
# Terminology:
# *Test case* refers to the artifacts obtained by applying a specific binary
# version to a specific QA dataset.
# *Test suite* refers to the set of test cases obtained from applying a specific
# binary version to all QA datasets.
# *QA project* refers to the folder containing a QA dataset and possibly
# related data.
# The *test suite identifier* is a sha1 and an additional index. The sha1
# identifies the binary version and the additional index allows to distinguish
# binaries that were generated form the same commit in a dirty repo
# (uncommitted changes).
#
# A folder for a test case is named in the following way:
#
#    <sha1>_<id>_<qaDatasetName>_<optionalDescription>
#
# <sha1> and <id> together form the test suite identifier, <qaDatasetName> is
# the name of the dataset converted to camel case, and <optionalDescription> is
# an optional description supplied by the user to make it easier to relate the
# test suits to the change that they test, e.g.,
#
#    1234567890_001_snowyHillside_increasedStepSizeTo42
