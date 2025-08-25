"""
Validator Agent for Task Verification

This agent is responsible for validating that completed tasks meet the original
goals and success criteria defined for the task.
"""

import json
from typing import Dict, Any, List, Tuple
from .base_agent import BaseAgent
from loguru import logger


class ValidationTool:
    """Tool for validating task completion against goals."""
    
    def __init__(self):
        self.name = "task_validator"
        self.description = "Validate task completion against original goals and success criteria"
    
    def __call__(self, task_definition: Dict[str, Any], execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate task completion.
        
        Args:
            task_definition: Original task definition with goals and criteria
            execution_result: Result from task execution
            
        Returns:
            Validation results
        """
        try:
            logger.info("Validating task completion")
            
            # Extract validation criteria
            original_goals = task_definition.get('goals', [])
            success_criteria = task_definition.get('success_criteria', [])
            expected_outcomes = task_definition.get('expected_outcomes', [])
            
            # Check execution success
            execution_success = execution_result.get('success', False)
            if not execution_success:
                return {
                    "validation_passed": False,
                    "reason": "Task execution failed",
                    "execution_error": execution_result.get('error', 'Unknown error'),
                    "validation_score": 0.0
                }
            
            # Validate against goals
            goal_validation = self._validate_goals(original_goals, execution_result)
            
            # Validate against success criteria
            criteria_validation = self._validate_success_criteria(success_criteria, execution_result)
            
            # Validate against expected outcomes
            outcome_validation = self._validate_expected_outcomes(expected_outcomes, execution_result)
            
            # Calculate overall validation score
            validation_score = self._calculate_validation_score(
                goal_validation, criteria_validation, outcome_validation
            )
            
            # Determine if validation passed
            validation_passed = validation_score >= 0.8  # 80% threshold
            
            validation_result = {
                "validation_passed": validation_passed,
                "validation_score": validation_score,
                "goal_validation": goal_validation,
                "criteria_validation": criteria_validation,
                "outcome_validation": outcome_validation,
                "overall_assessment": self._generate_assessment(validation_score),
                "recommendations": self._generate_recommendations(
                    goal_validation, criteria_validation, outcome_validation
                )
            }
            
            logger.info(f"Task validation completed. Score: {validation_score:.2f}, Passed: {validation_passed}")
            return validation_result
            
        except Exception as e:
            error_msg = f"Exception during task validation: {str(e)}"
            logger.error(error_msg)
            return {
                "validation_passed": False,
                "error": error_msg,
                "validation_score": 0.0
            }
    
    def _validate_goals(self, goals: List[str], execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate task completion against original goals."""
        validated_goals = []
        unvalidated_goals = []
        
        for goal in goals:
            # Simple keyword matching for goal validation
            # In a real implementation, this could use more sophisticated NLP
            goal_achieved = self._check_goal_achievement(goal, execution_result)
            
            if goal_achieved:
                validated_goals.append(goal)
            else:
                unvalidated_goals.append(goal)
        
        return {
            "total_goals": len(goals),
            "achieved_goals": validated_goals,
            "unachieved_goals": unvalidated_goals,
            "achievement_rate": len(validated_goals) / len(goals) if goals else 0.0
        }
    
    def _validate_success_criteria(self, criteria: List[Dict], execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate task completion against success criteria."""
        met_criteria = []
        unmet_criteria = []
        
        for criterion in criteria:
            criterion_text = criterion.get('text', '')
            criterion_met = self._check_criterion_met(criterion_text, execution_result)
            
            if criterion_met:
                met_criteria.append(criterion_text)
            else:
                unmet_criteria.append(criterion_text)
        
        return {
            "total_criteria": len(criteria),
            "met_criteria": met_criteria,
            "unmet_criteria": unmet_criteria,
            "completion_rate": len(met_criteria) / len(criteria) if criteria else 0.0
        }
    
    def _validate_expected_outcomes(self, outcomes: List[str], execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate task completion against expected outcomes."""
        achieved_outcomes = []
        unachieved_outcomes = []
        
        for outcome in outcomes:
            outcome_achieved = self._check_outcome_achievement(outcome, execution_result)
            
            if outcome_achieved:
                achieved_outcomes.append(outcome)
            else:
                unachieved_outcomes.append(outcome)
        
        return {
            "total_outcomes": len(outcomes),
            "achieved_outcomes": achieved_outcomes,
            "unachieved_outcomes": unachieved_outcomes,
            "achievement_rate": len(achieved_outcomes) / len(outcomes) if outcomes else 0.0
        }
    
    def _check_goal_achievement(self, goal: str, execution_result: Dict[str, Any]) -> bool:
        """Check if a specific goal was achieved."""
        # Simple implementation - check if goal keywords appear in execution output
        execution_output = execution_result.get('execution_output', '').lower()
        goal_keywords = goal.lower().split()
        
        # At least 50% of goal keywords should be present
        matching_keywords = sum(1 for keyword in goal_keywords if keyword in execution_output)
        return matching_keywords / len(goal_keywords) >= 0.5 if goal_keywords else False
    
    def _check_criterion_met(self, criterion: str, execution_result: Dict[str, Any]) -> bool:
        """Check if a success criterion was met."""
        # Similar to goal checking
        return self._check_goal_achievement(criterion, execution_result)
    
    def _check_outcome_achievement(self, outcome: str, execution_result: Dict[str, Any]) -> bool:
        """Check if an expected outcome was achieved."""
        # Similar to goal checking
        return self._check_goal_achievement(outcome, execution_result)
    
    def _calculate_validation_score(self, goal_validation: Dict, criteria_validation: Dict, outcome_validation: Dict) -> float:
        """Calculate overall validation score."""
        goal_score = goal_validation.get('achievement_rate', 0.0)
        criteria_score = criteria_validation.get('completion_rate', 0.0)
        outcome_score = outcome_validation.get('achievement_rate', 0.0)
        
        # Weighted average
        weights = [0.4, 0.4, 0.2]  # Goals and criteria are more important
        scores = [goal_score, criteria_score, outcome_score]
        
        weighted_score = sum(score * weight for score, weight in zip(scores, weights))
        return round(weighted_score, 3)
    
    def _generate_assessment(self, validation_score: float) -> str:
        """Generate human-readable assessment based on validation score."""
        if validation_score >= 0.9:
            return "Excellent - Task fully meets requirements"
        elif validation_score >= 0.8:
            return "Good - Task meets most requirements with minor issues"
        elif validation_score >= 0.7:
            return "Acceptable - Task meets basic requirements but needs improvement"
        elif validation_score >= 0.6:
            return "Marginal - Task partially meets requirements, significant issues"
        else:
            return "Poor - Task does not meet requirements"
    
    def _generate_recommendations(self, goal_validation: Dict, criteria_validation: Dict, outcome_validation: Dict) -> List[str]:
        """Generate recommendations for improvement."""
        recommendations = []
        
        if goal_validation.get('achievement_rate', 0.0) < 0.8:
            recommendations.append("Review and clarify task goals for better alignment")
        
        if criteria_validation.get('completion_rate', 0.0) < 0.8:
            recommendations.append("Refine success criteria to be more measurable")
        
        if outcome_validation.get('achievement_rate', 0.0) < 0.8:
            recommendations.append("Reassess expected outcomes and adjust task scope")
        
        if not recommendations:
            recommendations.append("Task meets requirements - no immediate action needed")
        
        return recommendations


class ValidatorAgent(BaseAgent):
    """Agent responsible for validating task completion against original goals."""
    
    def __init__(self):
        super().__init__(
            name="TaskValidator",
            role="Task Validation Specialist",
            goal="Ensure completed tasks meet original goals and success criteria",
            backstory="""You are an expert task validator with deep understanding of project 
            requirements and success metrics. You carefully assess task completion against 
            original goals and provide detailed feedback for improvement."""
        )
        
        # Add the validation tool
        self.validation_tool = ValidationTool()
        self.add_tool(self.validation_tool)
        
        logger.info("Validator Agent initialized with validation tool")
    
    def execute_task(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a completed task.
        
        Args:
            task_input: Task definition and execution results
            
        Returns:
            Validation results
        """
        try:
            logger.info(f"Validator Agent validating task: {task_input.get('task_id', 'Unknown')}")
            
            # Extract validation inputs
            task_definition = task_input.get('task_definition', {})
            execution_result = task_input.get('execution_result', {})
            
            if not task_definition or not execution_result:
                return {
                    "success": False,
                    "error": "Missing task definition or execution result",
                    "task_input": task_input
                }
            
            # Perform validation
            validation_result = self.validation_tool(task_definition, execution_result)
            
            # Add metadata
            validation_result.update({
                "validator_agent": self.name,
                "validation_timestamp": self._get_timestamp(),
                "task_id": task_input.get('task_id', 'Unknown')
            })
            
            logger.info(f"Task validation completed: {validation_result.get('validation_passed', False)}")
            return validation_result
            
        except Exception as e:
            error_msg = f"Exception during task validation: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "task_input": task_input
            }
    
    def _get_timestamp(self) -> str:
        """Get current timestamp for logging."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed status of the validator agent."""
        base_status = super().get_status()
        base_status.update({
            "validation_tool_available": hasattr(self, 'validation_tool')
        })
        return base_status
