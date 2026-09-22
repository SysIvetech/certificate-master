"""data_pipeline --id 옵션 테스트.

TDD: 특정 자격증 ID로 보강+임베딩을 실행할 수 있어야 함.
"""

import argparse


class TestDataPipelineIdOption:
    """--id 옵션 테스트."""

    def test_argparse_has_id_option(self):
        """argparse에 --id 옵션이 있어야 함."""
        import inspect

        from scripts.data_pipeline import main

        source = inspect.getsource(main)

        # --id 옵션이 parser에 정의되어 있어야 함
        assert (
            '"--id"' in source or "'--id'" in source
        ), "argparse에 --id 옵션이 정의되어 있어야 함"

    def test_id_option_accepts_uuid(self):
        """--id 옵션이 UUID를 받을 수 있어야 함."""
        parser = argparse.ArgumentParser()
        parser.add_argument("--id", type=str, help="자격증 ID")

        args = parser.parse_args(["--id", "4c9b057c-b129-4105-bd30-78886944f199"])
        assert args.id == "4c9b057c-b129-4105-bd30-78886944f199"

    def test_id_option_accepts_multiple_ids(self):
        """--id 옵션이 여러 ID를 받을 수 있어야 함."""
        parser = argparse.ArgumentParser()
        parser.add_argument("--id", type=str, nargs="+", help="자격증 ID 목록")

        args = parser.parse_args(
            [
                "--id",
                "id1",
                "id2",
                "id3",
            ]
        )
        assert args.id == ["id1", "id2", "id3"]


class TestDataPipelineRunWithIds:
    """ID 목록으로 파이프라인 실행 테스트."""

    def test_enrich_step_accepts_cert_ids(self):
        """enrich_step이 cert_ids 인자를 받아야 함."""
        import inspect

        from scripts.data_pipeline import DataPipeline

        sig = inspect.signature(DataPipeline.enrich_step)
        params = list(sig.parameters.keys())

        assert "cert_ids" in params, "enrich_step에 cert_ids 파라미터가 있어야 함"

    def test_embedding_step_accepts_cert_ids(self):
        """embedding_step이 cert_ids 인자를 받아야 함."""
        import inspect

        from scripts.data_pipeline import DataPipeline

        sig = inspect.signature(DataPipeline.embedding_step)
        params = list(sig.parameters.keys())

        assert "cert_ids" in params, "embedding_step에 cert_ids 파라미터가 있어야 함"

    def test_run_method_accepts_cert_ids(self):
        """run 메서드가 cert_ids 인자를 받아야 함."""
        import inspect

        from scripts.data_pipeline import DataPipeline

        sig = inspect.signature(DataPipeline.run)
        params = list(sig.parameters.keys())

        assert "cert_ids" in params, "run 메서드에 cert_ids 파라미터가 있어야 함"
