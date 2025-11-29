#!/usr/bin/env python3
"""
Service layer for database operations
Replaces file-based storage with database storage
"""


import json
import time
from typing import Optional, Dict, Any, List
from sqlalchemy import desc, func

from .models import (
    get_db,
    Collection,
    BenchmarkResult,
    BenchmarkRun,
    DocumentationVariant,
    TestCaseEvaluation
)


class BenchmarkResultService:
    """Service for managing benchmark results"""

    @staticmethod
    def create(
        run_id: str,
        model: str,
        model_id: str,
        variant: str,
        temperature: float,
        max_tokens: int,
        total_tests: int,
        responses: Dict[str, str],
        batch_size: Optional[int] = None,
        num_batches: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> int:
        """Save benchmark results to database"""
        with get_db() as session:
            result = BenchmarkResult(
                run_id=run_id,
                model=model,
                model_id=model_id,
                variant=variant,
                temperature=temperature,
                max_tokens=max_tokens,
                total_tests=total_tests,
                batch_size=batch_size,
                num_batches=num_batches,
                responses=responses,
                run_metadata=metadata,
                created_at=time.time(),
                status='completed'
            )
            session.add(result)
            session.flush()
            return result.id

    @staticmethod
    def set_evaluation_status(run_id: str, status: str):
        """Set evaluation status (pending, evaluating, completed, failed)"""
        with get_db() as session:
            result = session.query(BenchmarkResult).filter_by(run_id=run_id).first()
            if result:
                result.evaluation_status = status

    @staticmethod
    def update_evaluation(
        run_id: str,
        evaluation_results: Dict[str, Any],
        total_score: float,
        max_score: float,
        percentage: float
    ):
        """Update evaluation results for a benchmark"""
        with get_db() as session:
            result = session.query(BenchmarkResult).filter_by(run_id=run_id).first()
            if result:
                result.evaluation_results = evaluation_results
                result.total_score = total_score
                result.max_score = max_score
                result.percentage = percentage
                result.evaluated_at = time.time()
                result.evaluation_status = 'completed'

    @staticmethod
    def update_responses(run_id: str, responses: Dict[str, str]):
        """Update responses for a benchmark result"""
        with get_db() as session:
            result = session.query(BenchmarkResult).filter_by(run_id=run_id).first()
            if result:
                result.responses = responses
                result.evaluation_results = None
                result.total_score = None
                result.max_score = None
                result.percentage = None
                result.evaluated_at = None

    @staticmethod
    def get_by_run_id(run_id: str) -> Optional[Dict[str, Any]]:
        """Get benchmark result by run_id"""
        with get_db() as session:
            result = session.query(BenchmarkResult).filter_by(run_id=run_id).first()
            if result:
                return {
                    'id': result.id,
                    'run_id': result.run_id,
                    'model': result.model,
                    'model_id': result.model_id,
                    'variant': result.variant,
                    'temperature': result.temperature,
                    'max_tokens': result.max_tokens,
                    'total_tests': result.total_tests,
                    'batch_size': result.batch_size,
                    'num_batches': result.num_batches,
                    'responses': result.responses,
                    'metadata': result.run_metadata,
                    'evaluation_results': result.evaluation_results,
                    'total_score': result.total_score,
                    'max_score': result.max_score,
                    'percentage': result.percentage,
                    'created_at': result.created_at,
                    'evaluated_at': result.evaluated_at,
                    'status': result.status,
                    'evaluation_status': result.evaluation_status
                }
            return None

    @staticmethod
    def get_recent(limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent benchmark results"""
        with get_db() as session:
            results = session.query(BenchmarkResult).order_by(
                desc(BenchmarkResult.created_at)
            ).limit(limit).all()

            return [
                {
                    'id': r.id,
                    'run_id': r.run_id,
                    'model': r.model,
                    'variant': r.variant,
                    'total_tests': r.total_tests,
                    'total_score': r.total_score,
                    'max_score': r.max_score,
                    'percentage': r.percentage,
                    'created_at': r.created_at,
                    'responses': r.responses,
                    'collection': r.collection_obj.name if r.collection_obj else None,
                    'collection_id': r.collection_id
                }
                for r in results
            ]

    @staticmethod
    def get_by_model_variant(model: str, variant: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get results for specific model and variant"""
        with get_db() as session:
            results = session.query(BenchmarkResult).filter_by(
                model=model,
                variant=variant
            ).order_by(desc(BenchmarkResult.created_at)).limit(limit).all()

            return [
                {
                    'id': r.id,
                    'run_id': r.run_id,
                    'total_score': r.total_score,
                    'percentage': r.percentage,
                    'created_at': r.created_at
                }
                for r in results
            ]

    @staticmethod
    def get_stats() -> Dict[str, Any]:
        """Get aggregate statistics"""
        with get_db() as session:
            total = session.query(BenchmarkResult).count()

            avg_score = session.query(
                func.avg(BenchmarkResult.percentage)
            ).scalar() or 0

            top_models = session.query(
                BenchmarkResult.model,
                func.avg(BenchmarkResult.percentage).label('avg_score'),
                func.count(BenchmarkResult.id).label('count')
            ).group_by(BenchmarkResult.model).order_by(
                desc('avg_score')
            ).limit(5).all()

            return {
                'total_results': total,
                'average_score': round(avg_score, 2) if avg_score else 0,
                'top_models': [
                    {'model': m, 'avg_score': round(s, 2) if s else 0, 'count': c}
                    for m, s, c in top_models
                ]
            }

    @staticmethod
    def add_to_collection(run_ids: List[str], collection_name: str):
        """Add benchmark results to a collection"""
        collection_id = CollectionService.get_or_create(collection_name)
        with get_db() as session:
            session.query(BenchmarkResult).filter(
                BenchmarkResult.run_id.in_(run_ids)
            ).update({'collection_id': collection_id}, synchronize_session=False)

    @staticmethod
    def remove_from_collection(run_ids: List[str]):
        """Remove benchmark results from their collection"""
        with get_db() as session:
            session.query(BenchmarkResult).filter(
                BenchmarkResult.run_id.in_(run_ids)
            ).update({'collection_id': None}, synchronize_session=False)

    @staticmethod
    def get_collections() -> List[Dict[str, Any]]:
        """Get all collections with metadata"""
        return CollectionService.get_all()

    @staticmethod
    def get_collection_results(collection_name: str) -> List[Dict[str, Any]]:
        """Get all results in a collection by name"""
        with get_db() as session:
            collection = session.query(Collection).filter_by(name=collection_name).first()
            if not collection:
                return []

            results = session.query(BenchmarkResult).filter_by(
                collection_id=collection.id
            ).order_by(desc(BenchmarkResult.created_at)).all()

            return [
                {
                    'id': r.id,
                    'run_id': r.run_id,
                    'model': r.model,
                    'variant': r.variant,
                    'total_tests': r.total_tests,
                    'batch_size': r.batch_size,
                    'num_batches': r.num_batches,
                    'total_score': r.total_score,
                    'max_score': r.max_score,
                    'percentage': r.percentage,
                    'created_at': r.created_at,
                    'responses': r.responses,
                    'evaluation_results': r.evaluation_results
                }
                for r in results
            ]

    @staticmethod
    def delete_collection(collection_name: str):
        """Remove collection tag from all results (doesn't delete results)"""
        CollectionService.delete_by_name(collection_name)

    @staticmethod
    def delete_by_run_id(run_id: str) -> bool:
        """Delete a benchmark result by run_id"""
        with get_db() as session:
            result = session.query(BenchmarkResult).filter_by(run_id=run_id).first()
            if result:
                session.delete(result)
                return True
            return False


class BenchmarkRunService:
    """Service for managing benchmark runs"""

    @staticmethod
    def create(
        run_id: str,
        model: str,
        model_id: str,
        variant: str,
        temperature: float,
        max_tokens: int
    ) -> int:
        """Create new benchmark run"""
        with get_db() as session:
            run = BenchmarkRun(
                run_id=run_id,
                model=model,
                model_id=model_id,
                variant=variant,
                temperature=temperature,
                max_tokens=max_tokens,
                status='running',
                started_at=time.time()
            )
            session.add(run)
            session.flush()
            return run.id

    @staticmethod
    def update_progress(run_id: str, progress: str):
        """Update run progress"""
        with get_db() as session:
            run = session.query(BenchmarkRun).filter_by(run_id=run_id).first()
            if run:
                run.progress = progress

    @staticmethod
    def complete(run_id: str, result_id: Optional[int] = None):
        """Mark run as completed"""
        with get_db() as session:
            run = session.query(BenchmarkRun).filter_by(run_id=run_id).first()
            if run:
                run.status = 'completed'
                run.completed_at = time.time()
                run.result_id = result_id

    @staticmethod
    def fail(run_id: str, error_message: str):
        """Mark run as failed"""
        with get_db() as session:
            run = session.query(BenchmarkRun).filter_by(run_id=run_id).first()
            if run:
                run.status = 'failed'
                run.completed_at = time.time()
                run.error_message = error_message

    @staticmethod
    def get_active_runs() -> List[Dict[str, Any]]:
        """Get all running benchmarks"""
        with get_db() as session:
            runs = session.query(BenchmarkRun).filter_by(status='running').all()

            return [
                {
                    'run_id': r.run_id,
                    'model': r.model,
                    'variant': r.variant,
                    'progress': r.progress,
                    'started_at': r.started_at
                }
                for r in runs
            ]






class DocumentationService:
    """Service for managing documentation variants"""

    @staticmethod
    def create_variant(variant_name: str, url: str, version: str, description: Optional[str] = None):
        """Create a new documentation variant with URL"""
        with get_db() as session:
            existing = session.query(DocumentationVariant).filter_by(
                variant_name=variant_name
            ).first()

            if existing:
                existing.url = url
                existing.version = version
                existing.description = description
                existing.updated_at = time.time()
            else:
                variant = DocumentationVariant(
                    variant_name=variant_name,
                    url=url,
                    version=version,
                    description=description,
                    created_at=time.time(),
                    updated_at=time.time(),
                    is_active=True
                )
                session.add(variant)

    @staticmethod
    def get_variant(variant_name: str, force_refresh: bool = False) -> Optional[str]:
        """Get documentation content by variant name, fetching from URL if needed"""
        import requests

        with get_db() as session:
            variant = session.query(DocumentationVariant).filter_by(
                variant_name=variant_name,
                is_active=True
            ).first()

            if not variant:
                return None

            # Check if cache is valid
            current_time = time.time()
            cache_valid = (
                variant.content and
                variant.cached_at and
                (current_time - variant.cached_at) < variant.cache_ttl and
                not force_refresh
            )

            if cache_valid:
                return variant.content

            # Fetch from URL
            try:
                response = requests.get(variant.url, timeout=30)
                response.raise_for_status()
                content = response.text

                # Update cache
                variant.content = content
                variant.size_bytes = len(content.encode('utf-8'))
                variant.cached_at = current_time
                session.commit()

                return content
            except Exception as e:
                print(f"Error fetching variant {variant_name} from {variant.url}: {e}")
                # Return cached content if available, even if expired
                return variant.content if variant.content else None

    @staticmethod
    def get_all_variants() -> List[Dict[str, Any]]:
        """Get all active documentation variants"""
        with get_db() as session:
            variants = session.query(DocumentationVariant).filter_by(
                is_active=True
            ).all()

            return [
                {
                    'name': v.variant_name,
                    'version': v.version,
                    'url': v.url,
                    'size_bytes': v.size_bytes or 0,
                    'size_kb': round((v.size_bytes or 0) / 1024, 2)
                }
                for v in variants
            ]


class CollectionService:
    """Service for managing collections"""

    @staticmethod
    def get_or_create(name: str, description: Optional[str] = None) -> int:
        """Get existing collection or create new one by name"""
        with get_db() as session:
            collection = session.query(Collection).filter_by(name=name).first()
            if collection:
                return collection.id

            collection = Collection(
                name=name,
                description=description,
                created_at=time.time()
            )
            session.add(collection)
            session.flush()
            return collection.id

    @staticmethod
    def get_all() -> List[Dict[str, Any]]:
        """Get all collections with metadata"""
        with get_db() as session:
            collections = session.query(
                Collection.id,
                Collection.name,
                Collection.description,
                Collection.created_at,
                func.count(BenchmarkResult.id).label('count'),
                func.avg(BenchmarkResult.percentage).label('avg_score')
            ).outerjoin(
                BenchmarkResult, BenchmarkResult.collection_id == Collection.id
            ).group_by(
                Collection.id, Collection.name, Collection.description, Collection.created_at
            ).order_by(
                desc(Collection.created_at)
            ).all()

            result_list = []
            for coll_id, name, description, created, count, avg_score in collections:
                # Get first result to extract metadata
                first_result = session.query(BenchmarkResult).filter_by(
                    collection_id=coll_id
                ).first()

                metadata = None
                if first_result:
                    metadata = {
                        'model': first_result.model,
                        'model_full': first_result.model,
                        'variant': first_result.variant,
                        'total_tests': str(first_result.total_tests),
                        'batch_size': first_result.batch_size
                    }

                result_list.append({
                    'id': coll_id,
                    'name': name,
                    'path': f'collections/{name}',
                    'description': description,
                    'created': created,
                    'file_count': count,
                    'count': count,  # Keep for backward compatibility
                    'avg_score': round(avg_score, 2) if avg_score else 0,
                    'metadata': metadata
                })

            return result_list

    @staticmethod
    def delete(collection_id: int):
        """Delete a collection and unlink all results"""
        with get_db() as session:
            session.query(BenchmarkResult).filter_by(
                collection_id=collection_id
            ).update({'collection_id': None}, synchronize_session=False)

            session.query(Collection).filter_by(id=collection_id).delete()

    @staticmethod
    def delete_by_name(name: str):
        """Delete a collection by name and unlink all results"""
        with get_db() as session:
            collection = session.query(Collection).filter_by(name=name).first()
            if collection:
                session.query(BenchmarkResult).filter_by(
                    collection_id=collection.id
                ).update({'collection_id': None}, synchronize_session=False)

                session.query(Collection).filter_by(name=name).delete()


class TestCaseEvaluationService:
    """Service for managing individual test case evaluations"""

    @staticmethod
    def save_evaluations(
        benchmark_result_id: int,
        evaluations: List[Dict[str, Any]]
    ):
        """Save multiple test case evaluations"""
        with get_db() as session:
            # Delete existing evaluations for this result
            session.query(TestCaseEvaluation).filter_by(
                benchmark_result_id=benchmark_result_id
            ).delete()

            # Add new evaluations
            for eval_data in evaluations:
                evaluation = TestCaseEvaluation(
                    benchmark_result_id=benchmark_result_id,
                    test_id=eval_data['test_id'],
                    test_category=eval_data.get('test_category'),
                    test_level=eval_data.get('test_level'),
                    test_description=eval_data.get('test_description'),
                    code_response=eval_data['code_response'],
                    passed=eval_data['passed'],
                    score=eval_data['score'],
                    max_score=eval_data['max_score'],
                    passed_checks=eval_data.get('passed_checks', []),
                    failed_checks=eval_data.get('failed_checks', []),
                    evaluation_details=eval_data.get('evaluation_details'),
                    evaluated_at=time.time()
                )
                session.add(evaluation)

    @staticmethod
    def get_by_benchmark_result(benchmark_result_id: int) -> List[Dict[str, Any]]:
        """Get all test case evaluations for a benchmark result"""
        with get_db() as session:
            evaluations = session.query(TestCaseEvaluation).filter_by(
                benchmark_result_id=benchmark_result_id
            ).all()

            return [
                {
                    'test_id': e.test_id,
                    'test_category': e.test_category,
                    'test_level': e.test_level,
                    'test_description': e.test_description,
                    'code_response': e.code_response,
                    'passed': e.passed,
                    'score': e.score,
                    'max_score': e.max_score,
                    'passed_checks': e.passed_checks,
                    'failed_checks': e.failed_checks,
                    'evaluation_details': e.evaluation_details,
                    'evaluated_at': e.evaluated_at
                }
                for e in evaluations
            ]
